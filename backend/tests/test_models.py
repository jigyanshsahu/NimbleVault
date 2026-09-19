"""
Unit tests for VideoJob models and validation schemas.
"""
from datetime import datetime, timezone
import pytest

from app.models.video import (
    JobStatus,
    VideoJob,
    VideoJobSchema,
)


def test_job_status_enum_values():
    """Verify all 6 pipeline lifecycle statuses exist."""
    assert JobStatus.PENDING.value == "PENDING"
    assert JobStatus.DOWNLOADING.value == "DOWNLOADING"
    assert JobStatus.TITLING.value == "TITLING"
    assert JobStatus.UPLOADING.value == "UPLOADING"
    assert JobStatus.COMPLETED.value == "COMPLETED"
    assert JobStatus.FAILED.value == "FAILED"


def test_video_job_orm_instantiation():
    """Verify VideoJob ORM model defaults and attributes."""
    job = VideoJob(
        drive_file_id="drive-999",
        file_name="intro.mp4",
        full_path="Drive/Tutorials/intro.mp4",
        status=JobStatus.PENDING.value,
    )
    assert job.drive_file_id == "drive-999"
    assert job.file_name == "intro.mp4"
    assert job.status == "PENDING"
    assert job.youtube_url is None

    job.youtube_video_id = "abc123vid"
    assert job.youtube_url == "https://www.youtube.com/watch?v=abc123vid"


def test_video_job_schema_youtube_url_computation():
    """Verify youtube_url computed property in VideoJobSchema."""
    now = datetime.now(timezone.utc)
    job_with_id = VideoJobSchema(
        id="test-uuid",
        drive_file_id="drive-123",
        file_name="video.mp4",
        full_path="Drive/video.mp4",
        status="COMPLETED",
        youtube_video_id="dQw4w9WgXcQ",
        created_at=now,
        updated_at=now,
    )
    assert job_with_id.youtube_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    job_without_id = VideoJobSchema(
        id="test-uuid-2",
        drive_file_id="drive-456",
        file_name="clip.mov",
        full_path="Drive/clip.mov",
        status="PENDING",
        youtube_video_id=None,
        created_at=now,
        updated_at=now,
    )
    assert job_without_id.youtube_url is None
