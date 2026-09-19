"""
NimbleVault – FastAPI Route Handlers
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, get_db_context
from app.models.video import (
    JobStatus,
    ScanRequest,
    UpdateTitleRequest,
    VideoJob,
    VideoJobPublic,
)
from app.services.drive_service import DriveService
from app.services.gemini_service import GeminiService
from app.services.youtube_service import YouTubeService

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api")

# ── Dependency singletons (created once per process) ──────────────────────────

_drive_service: DriveService | None = None
_gemini_service: GeminiService | None = None
_youtube_service: YouTubeService | None = None


def get_drive_service() -> DriveService:
    global _drive_service
    if _drive_service is None:
        _drive_service = DriveService()
    return _drive_service


def get_gemini_service() -> GeminiService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service


def get_youtube_service() -> YouTubeService:
    global _youtube_service
    if _youtube_service is None:
        _youtube_service = YouTubeService()
    return _youtube_service


# ── Helper: set job status ─────────────────────────────────────────────────────

async def _set_status(
    db: AsyncSession,
    job: VideoJob,
    new_status: JobStatus,
    error: str | None = None,
) -> None:
    job.status = new_status.value
    if error:
        job.error_log = error
    db.add(job)
    await db.commit()
    await db.refresh(job)


# ── Background processing pipeline ────────────────────────────────────────────

async def _process_job(job_id: str) -> None:
    """
    Full pipeline for a single video job (runs in background):
    PENDING → DOWNLOADING → TITLING → UPLOADING → COMPLETED (or FAILED)
    """
    drive = get_drive_service()
    gemini = get_gemini_service()
    youtube = get_youtube_service()

    tmp_dir = Path(settings.TEMP_DOWNLOAD_DIR)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    async with get_db_context() as db:
        result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
        job: VideoJob | None = result.scalar_one_or_none()
        if job is None:
            logger.error("Job %s not found; aborting pipeline.", job_id)
            return

        local_path: Path | None = None

        try:
            # ── 1. Download ────────────────────────────────────────────────────
            await _set_status(db, job, JobStatus.DOWNLOADING)
            local_path = tmp_dir / f"{job_id}_{job.file_name}"
            await drive.download_file(job.drive_file_id, local_path)
            logger.info("[%s] Download complete.", job_id)

            # ── 2. Title generation ────────────────────────────────────────────
            await _set_status(db, job, JobStatus.TITLING)
            if not job.generated_title:
                # Only generate if no manual override has been set
                title = await gemini.generate_title(job.full_path)
                job.generated_title = title
                db.add(job)
                await db.commit()
                await db.refresh(job)
            logger.info("[%s] Title: %s", job_id, job.generated_title)

            # ── 3. Upload to YouTube ───────────────────────────────────────────
            await _set_status(db, job, JobStatus.UPLOADING)
            video_id = await youtube.upload_video(
                file_path=local_path,
                title=job.generated_title or job.file_name,
                description=f"Source: {job.full_path}",
                tags=["nimblevault", "automated"],
            )
            job.youtube_video_id = video_id
            job.status = JobStatus.COMPLETED.value
            job.error_log = None
            db.add(job)
            await db.commit()
            logger.info("[%s] COMPLETED – YouTube ID: %s", job_id, video_id)

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.exception("[%s] Pipeline failed: %s", job_id, error_msg)
            await _set_status(db, job, JobStatus.FAILED, error=error_msg)

        finally:
            # ── 4. Cleanup local file ──────────────────────────────────────────
            if local_path and local_path.exists():
                local_path.unlink(missing_ok=True)
                logger.info("[%s] Temp file removed.", job_id)


# ── Routes ─────────────────────────────────────────────────────────────────────


@router.post("/scan", response_model=list[VideoJobPublic], status_code=status.HTTP_201_CREATED)
async def scan_folder(
    body: ScanRequest,
    db: AsyncSession = Depends(get_db),
    drive: DriveService = Depends(get_drive_service),
) -> list[VideoJobPublic]:
    """
    Recursively scan a Drive folder, persist new video files as PENDING jobs,
    and skip any already-known drive_file_id values (duplicate prevention).
    """
    # Fetch all existing drive_file_ids from DB to prevent duplicates
    existing_result = await db.execute(
        select(VideoJob.drive_file_id)
    )
    existing_ids: set[str] = {row[0] for row in existing_result.fetchall()}

    # Scan Drive
    try:
        drive_files = await drive.list_videos_recursive(body.folder_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Drive scan failed: {exc}",
        )

    new_jobs: list[VideoJob] = []
    for df in drive_files:
        if df.file_id in existing_ids:
            logger.info("Skipping already-indexed file: %s", df.file_id)
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

    logger.info("Scan complete – %d new jobs added.", len(new_jobs))
    return [VideoJobPublic.from_orm_with_url(j) for j in new_jobs]


@router.get("/jobs", response_model=list[VideoJobPublic])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
) -> list[VideoJobPublic]:
    """Return all video jobs sorted by creation date (newest first)."""
    result = await db.execute(
        select(VideoJob).order_by(VideoJob.created_at.desc())
    )
    jobs = result.scalars().all()
    return [VideoJobPublic.from_orm_with_url(j) for j in jobs]


@router.patch("/jobs/{job_id}/title", response_model=VideoJobPublic)
async def update_job_title(
    job_id: str,
    body: UpdateTitleRequest,
    db: AsyncSession = Depends(get_db),
) -> VideoJobPublic:
    """Allow inline editing of the AI-generated title before upload."""
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job: VideoJob | None = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (JobStatus.PENDING.value, JobStatus.FAILED.value):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot edit title when job is in '{job.status}' state",
        )
    job.generated_title = body.title
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return VideoJobPublic.from_orm_with_url(job)


@router.post("/process/{job_id}", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def process_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enqueue the full pipeline for a single job."""
    result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
    job: VideoJob | None = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in (JobStatus.PENDING.value, JobStatus.FAILED.value):
        raise HTTPException(
            status_code=400,
            detail=f"Job is already in '{job.status}' state",
        )

    background_tasks.add_task(_process_job, job_id)
    return {"message": "Processing started", "job_id": job_id}


@router.post("/process-batch", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def process_batch(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Sequentially enqueue all PENDING jobs for processing."""
    result = await db.execute(
        select(VideoJob)
        .where(VideoJob.status == JobStatus.PENDING.value)
        .order_by(VideoJob.created_at.asc())
    )
    pending_jobs = result.scalars().all()

    if not pending_jobs:
        return {"message": "No pending jobs to process", "queued": 0}

    async def _sequential_pipeline(job_ids: list[str]) -> None:
        for jid in job_ids:
            await _process_job(jid)

    job_ids = [j.id for j in pending_jobs]
    background_tasks.add_task(_sequential_pipeline, job_ids)

    return {
        "message": f"Batch processing started for {len(job_ids)} jobs",
        "queued": len(job_ids),
        "job_ids": job_ids,
    }
