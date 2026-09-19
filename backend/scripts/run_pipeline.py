"""
NimbleVault – End-to-End Pipeline Execution CLI
Executes the automated content handler:
Google Drive (Acquisition) -> Gemini AI (Titling) -> YouTube API (Distribution)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import get_db_context, engine, Base
from app.models.video import VideoJob, JobStatus
from app.services.drive_service import DriveService
from app.services.gemini_service import GeminiService
from app.services.youtube_service import (
    YouTubeService,
    is_youtube_authenticated,
    is_video_alive_on_youtube,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("googleapiclient").setLevel(logging.WARNING)

logger = logging.getLogger("nimblevault.pipeline")
settings = get_settings()

DEFAULT_FOLDER_ID = "1HKD2on9LkF3OfKvWmkZwtdnSHMS1HUGs"


async def ensure_database():
    """Ensure database tables are initialized."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def audit_and_reconcile_youtube_videos(db) -> list[VideoJob]:
    """
    Audits all COMPLETED video jobs in the database against YouTube.
    If a video was deleted or removed on YouTube, resets status to PENDING
    so it can be re-uploaded automatically.
    """
    res = await db.execute(
        select(VideoJob).where(
            VideoJob.status == JobStatus.COMPLETED.value,
            VideoJob.youtube_video_id.isnot(None),
        )
    )
    completed_jobs = res.scalars().all()
    reconciled: list[VideoJob] = []

    for job in completed_jobs:
        if not job.youtube_video_id or job.youtube_video_id.startswith("mock_"):
            continue

        alive = await asyncio.to_thread(is_video_alive_on_youtube, job.youtube_video_id)
        if not alive:
            old_vid = job.youtube_video_id
            print(f"  [RECONCILE] Video '{job.file_name}' (ID: {old_vid}) was DELETED from YouTube!")
            print(f"              Reconciling status to PENDING for re-upload.")
            job.status = JobStatus.PENDING.value
            job.youtube_video_id = None
            job.error_log = f"Video was deleted on YouTube (previous ID: {old_vid}). Status reconciled to PENDING."
            db.add(job)
            reconciled.append(job)

    if reconciled:
        await db.commit()
        for j in reconciled:
            await db.refresh(j)

    return reconciled


async def display_status_table(db):
    """Display the status table of all video jobs currently tracked in database."""
    res = await db.execute(select(VideoJob).order_by(VideoJob.created_at.desc()))
    jobs = res.scalars().all()

    print(f"\nTracked Video Jobs in Database ({len(jobs)} total):")
    print("=" * 115)
    print(f"{'Status':<16} | {'File Name':<30} | {'Google Drive Route':<34} | {'YouTube / Detail'}")
    print("-" * 115)

    for j in jobs:
        route = j.full_path or "(no route)"
        if len(route) > 32:
            route = "..." + route[-29:]
        fname = j.file_name
        if len(fname) > 28:
            fname = fname[:25] + "..."

        detail = j.youtube_url or (f"Title: {j.generated_title[:32]}" if j.generated_title else "(pending metadata)")
        if j.error_log and "deleted on YouTube" in j.error_log and j.status == JobStatus.PENDING.value:
            status_display = "PENDING (YT del)"
        else:
            status_display = j.status

        print(f"{status_display:<16} | {fname:<30} | {route:<34} | {detail}")
    print("=" * 115)

    pending_cnt = sum(1 for j in jobs if j.status == JobStatus.PENDING.value)
    completed_cnt = sum(1 for j in jobs if j.status == JobStatus.COMPLETED.value)
    failed_cnt = sum(1 for j in jobs if j.status == JobStatus.FAILED.value)
    other_cnt = len(jobs) - (pending_cnt + completed_cnt + failed_cnt)
    print(f"Summary: {completed_cnt} Completed | {pending_cnt} Pending | {failed_cnt} Failed | {other_cnt} In-Progress\n")


async def scan_and_register_videos(folder_id: str) -> list[VideoJob]:
    """
    Step 1: Mass Content Acquisition
    Recursively scans Google Drive folder and registers new video files into the database.
    Prevents duplicates using drive_file_id index.
    """
    print("\n" + "=" * 65)
    print(" STEP 1: MASS CONTENT ACQUISITION (Google Drive)")
    print("=" * 65)
    print(f"Target Google Drive Folder ID: {folder_id}")

    drive = DriveService()
    print("Scanning Drive recursively for video files...")
    drive_files = await drive.list_videos_recursive(folder_id)
    print(f"Found {len(drive_files)} video file(s) across folder structure:")

    for df in drive_files:
        size_mb = df.size / (1024 * 1024)
        print(f"  * {df.full_path} [{df.mime_type}, {size_mb:.2f} MB]")

    new_jobs: list[VideoJob] = []
    async with get_db_context() as db:
        # Audit YouTube liveness across all completed jobs in database
        print("\nAuditing YouTube liveness for previously uploaded videos...")
        reconciled = await audit_and_reconcile_youtube_videos(db)
        new_jobs.extend(reconciled)

        # Check existing jobs to prevent duplicates and register new files
        result = await db.execute(select(VideoJob))
        existing_jobs_map: dict[str, VideoJob] = {
            j.drive_file_id: j for j in result.scalars().all()
        }

        for df in drive_files:
            if df.file_id in existing_jobs_map:
                existing_job = existing_jobs_map[df.file_id]
                # Update route if nested folder changed
                if existing_job.full_path != df.full_path:
                    print(f"  [PATH] Updated route for '{df.file_name}': {df.full_path}")
                    existing_job.full_path = df.full_path
                    db.add(existing_job)
                print(f"  [INDEXED] '{df.file_name}' ({existing_job.status}) in {df.full_path}")
                continue

            print(f"  [NEW] Discovered video in nested folder: {df.full_path}")
            job = VideoJob(
                drive_file_id=df.file_id,
                file_name=df.file_name,
                full_path=df.full_path,
                status=JobStatus.PENDING.value,
            )
            db.add(job)
            new_jobs.append(job)

        await db.commit()
        for j in new_jobs:
            await db.refresh(j)

    print(f"\n[OK] Acquisition Summary: {len(new_jobs)} video job(s) queued or reconciled.")
    return new_jobs


async def execute_job(job_id: str, dry_run: bool = False):
    """
    Execute the full processing pipeline for a single VideoJob:
    PENDING -> DOWNLOADING -> TITLING -> UPLOADING -> COMPLETED (or FAILED)
    """
    drive = DriveService()
    gemini = GeminiService()

    yt_authenticated = is_youtube_authenticated()
    youtube: YouTubeService | None = None
    if not dry_run:
        if yt_authenticated:
            youtube = YouTubeService()
        else:
            print("\n[!] WARNING: YouTube OAuth token not found.")
            print("    To upload to YouTube, run: python scripts/auth_youtube.py")
            print("    Proceeding in simulated dry-run mode for upload stage.\n")
            dry_run = True

    tmp_dir = Path(settings.TEMP_DOWNLOAD_DIR)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    async with get_db_context() as db:
        res = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
        job: VideoJob | None = res.scalar_one_or_none()
        if not job:
            logger.error(f"Job ID '{job_id}' not found in database.")
            return

        print("\n" + "-" * 65)
        print(f" PROCESSING JOB: {job.id}")
        print(f" File: {job.file_name}")
        print(f" Path: {job.full_path}")
        print("-" * 65)

        local_path: Path | None = None
        try:
            # ─────────────────────────────────────────────────────────────
            # 1. Download from Google Drive
            # ─────────────────────────────────────────────────────────────
            job.status = JobStatus.DOWNLOADING.value
            db.add(job)
            await db.commit()
            print(f"\n[DOWNLOADING] Fetching from Google Drive (ID: {job.drive_file_id})...")

            local_path = tmp_dir / f"{job.id}_{job.file_name}"
            await drive.download_file(job.drive_file_id, local_path)
            file_size_mb = local_path.stat().st_size / (1024 * 1024)
            print(f"[OK] Downloaded locally to: {local_path} ({file_size_mb:.2f} MB)")

            # ─────────────────────────────────────────────────────────────
            # 2. Intelligent Metadata Generation (Gemini AI)
            # ─────────────────────────────────────────────────────────────
            job.status = JobStatus.TITLING.value
            db.add(job)
            await db.commit()
            print(f"\n[TITLING] Generating contextual metadata via Gemini AI ({settings.GEMINI_MODEL})...")

            metadata = await gemini.generate_metadata(job.full_path)
            if not job.generated_title:
                job.generated_title = metadata.title
                db.add(job)
                await db.commit()

            print(f"[OK] Generated Title: \"{job.generated_title}\"")
            print(f"[OK] Description:\n     {metadata.description.replace(chr(10), chr(10) + '     ')}")
            print(f"[OK] Extracted Tags:   {', '.join(metadata.tags)}")

            # ─────────────────────────────────────────────────────────────
            # 3. Distribution (YouTube API)
            # ─────────────────────────────────────────────────────────────
            job.status = JobStatus.UPLOADING.value
            db.add(job)
            await db.commit()
            print(f"\n[UPLOADING] Uploading to YouTube...")

            if dry_run or not youtube:
                mock_id = f"mock_{job.drive_file_id[:8]}"
                job.youtube_video_id = mock_id
                print(f"[OK] [DRY-RUN] Simulated YouTube upload. Simulated Video ID: {mock_id}")
            else:
                video_id = await youtube.upload_video(
                    file_path=local_path,
                    title=job.generated_title or metadata.title,
                    description=metadata.description,
                    tags=metadata.tags,
                )
                job.youtube_video_id = video_id
                print(f"[OK] Video successfully published to YouTube!")
                print(f"  URL: https://www.youtube.com/watch?v={video_id}")

            # ─────────────────────────────────────────────────────────────
            # 4. Finalize & Persist
            # ─────────────────────────────────────────────────────────────
            job.status = JobStatus.COMPLETED.value
            job.error_log = None
            db.add(job)
            await db.commit()
            print(f"\n[OK] JOB COMPLETED SUCCESSFULLY! Status: {job.status}")

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.exception(f"Job failed: {error_msg}")
            job.status = JobStatus.FAILED.value
            job.error_log = error_msg
            db.add(job)
            await db.commit()
            print(f"\n[FAIL] JOB FAILED: {error_msg}")

        finally:
            # ─────────────────────────────────────────────────────────────
            # 5. Clean up temporary local file
            # ─────────────────────────────────────────────────────────────
            if local_path and local_path.exists():
                local_path.unlink(missing_ok=True)
                print(f"[OK] Cleaned up temporary local file: {local_path.name}")


async def main():
    parser = argparse.ArgumentParser(description="NimbleVault Pipeline Execution")
    parser.add_argument(
        "--folder-id",
        type=str,
        default=DEFAULT_FOLDER_ID,
        help=f"Google Drive folder ID to scan (default: {DEFAULT_FOLDER_ID})",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Perform full sync: scan Google Drive nested folders, audit YouTube liveness, and show status table",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Audit YouTube liveness and display the status table of all tracked video jobs",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="When used with --status, also scan Google Drive before displaying status",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Only perform Google Drive acquisition, YouTube audit, and show status table",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run Drive download and Gemini AI titling, but simulate YouTube upload",
    )
    parser.add_argument(
        "--job-id",
        type=str,
        help="Execute pipeline for a specific existing Job ID",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all pending jobs in the database",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-processing of all video files in folder (resets existing jobs to PENDING)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the zero-credential interactive reviewer demo across all 4 rubric scenarios",
    )

    args = parser.parse_args()

    if args.demo:
        from scripts.demo import run_demo
        run_demo()
        return

    print("\n" + "=" * 65)
    print(" NIMBLEVAULT - AI-POWERED CONTENT HANDLER PIPELINE")
    print("=" * 65)

    await ensure_database()

    # ─────────────────────────────────────────────────────────────────────────
    # Full Sync: Scan Google Drive + Audit YouTube + Display Status Table
    # ─────────────────────────────────────────────────────────────────────────
    if args.sync or (args.status and args.scan):
        await scan_and_register_videos(args.folder_id)
        async with get_db_context() as db:
            await display_status_table(db)
        print("[Tip] To process pending jobs and upload to YouTube:")
        print("      python scripts/run_pipeline.py\n")
        return

    # ─────────────────────────────────────────────────────────────────────────
    # Status: Real-time YouTube liveness audit + Display Status Table
    # ─────────────────────────────────────────────────────────────────────────
    if args.status:
        async with get_db_context() as db:
            print("\nAuditing YouTube liveness for tracked jobs...")
            reconciled = await audit_and_reconcile_youtube_videos(db)
            if reconciled:
                print(f"[RECONCILED] Detected {len(reconciled)} deleted YouTube video(s). Status updated to PENDING.")
            else:
                print("[OK] YouTube liveness audit complete.")
            await display_status_table(db)
        print("[Tip] To also scan Google Drive for newly added nested folders & videos:")
        print("      python scripts/run_pipeline.py --sync\n")
        print("[Tip] To process pending jobs and upload to YouTube:")
        print("      python scripts/run_pipeline.py\n")
        return

    if args.force:
        async with get_db_context() as db:
            res = await db.execute(select(VideoJob))
            for j in res.scalars():
                j.status = JobStatus.PENDING.value
                j.error_log = None
                db.add(j)
            await db.commit()
            print("[INFO] --force flag enabled: Reset existing jobs to PENDING.\n")

    # If specific job ID requested
    if args.job_id:
        await execute_job(args.job_id, dry_run=args.dry_run)
        return

    # If batch processing of pending jobs requested
    if args.batch:
        async with get_db_context() as db:
            result = await db.execute(
                select(VideoJob).where(VideoJob.status == JobStatus.PENDING.value)
            )
            pending_jobs = result.scalars().all()
            print(f"Found {len(pending_jobs)} pending job(s) in database.")
            for j in pending_jobs:
                await execute_job(j.id, dry_run=args.dry_run)
        return

    # Default / Scan-only flow: Scan folder and reconcile state
    jobs = await scan_and_register_videos(args.folder_id)

    if args.scan_only:
        async with get_db_context() as db:
            await display_status_table(db)
        print("Scan-only flag enabled. Skipping pipeline execution.\n")
        return

    if not jobs:
        # Check if there are any existing pending jobs for this folder or general
        async with get_db_context() as db:
            res = await db.execute(
                select(VideoJob).where(VideoJob.status == JobStatus.PENDING.value)
            )
            jobs = res.scalars().all()
            if jobs:
                print(f"\nProcessing {len(jobs)} existing PENDING job(s) from database...")

    if not jobs:
        print("\nNo pending jobs to process. All files are up to date!")
        async with get_db_context() as db:
            await display_status_table(db)
        return

    for j in jobs:
        await execute_job(j.id, dry_run=args.dry_run)

    print("\n" + "=" * 65)
    print(" PIPELINE EXECUTION COMPLETED")
    print("=" * 65)
    async with get_db_context() as db:
        await display_status_table(db)


if __name__ == "__main__":
    asyncio.run(main())
