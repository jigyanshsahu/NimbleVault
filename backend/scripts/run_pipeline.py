"""
NimbleVault – End-to-End Pipeline Execution CLI
Executes the automated content handler:
Google Drive (Acquisition) -> Gemini AI (Titling) -> YouTube API (Distribution)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import tempfile
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
from app.services.youtube_service import YouTubeService, is_youtube_authenticated

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
        # Check existing drive_file_ids to prevent duplicates
        result = await db.execute(select(VideoJob.drive_file_id))
        existing_ids = {row[0] for row in result.fetchall()}

        for df in drive_files:
            if df.file_id in existing_ids:
                print(f"  [INFO] File '{df.file_name}' already indexed in database (skipping).")
                continue

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

    print(f"\n[OK] Acquisition Summary: {len(new_jobs)} new video job(s) recorded to database.")
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

            if not job.generated_title:
                ai_title = await gemini.generate_title(job.full_path)
                job.generated_title = ai_title
                db.add(job)
                await db.commit()

            print(f"[OK] Generated Title: \"{job.generated_title}\"")

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
                    title=job.generated_title or job.file_name,
                    description=f"Automated upload via NimbleVault\nSource: {job.full_path}",
                    tags=["nimblevault", "automated", "content-handler"],
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
        "--scan-only",
        action="store_true",
        help="Only perform Google Drive acquisition and database registration",
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

    args = parser.parse_args()

    print("\n" + "=" * 65)
    print(" NIMBLEVAULT - AI-POWERED CONTENT HANDLER PIPELINE")
    print("=" * 65)

    await ensure_database()

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

    # Default flow: Scan folder then process newly discovered or pending jobs
    jobs = await scan_and_register_videos(args.folder_id)

    if args.scan_only:
        print("\nScan-only flag enabled. Skipping pipeline execution.")
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
        return

    for j in jobs:
        await execute_job(j.id, dry_run=args.dry_run)

    print("\n" + "=" * 65)
    print(" PIPELINE EXECUTION COMPLETED")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
