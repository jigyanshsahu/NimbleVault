"""
Unit tests for VideoJob models and validation schemas.
"""
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone

from app.models.video import (
    JobStatus,
    ScanRequest,
    UpdateTitleRequest,
    VideoJobSchema,
    VideoJobPublic,
)


def test_job_status_enum_values():
    """Verify all 6 pipeline lifecycle statuses exist."""
    assert JobStatus.PENDING.value == "PENDING"
    assert JobStatus.DOWNLOADING.value == "DOWNLOADING"
    assert JobStatus.TITLING.value == "TITLING"
    assert JobStatus.UPLOADING.value == "UPLOADING"
    assert JobStatus.COMPLETED.value == "COMPLETED"
    assert JobStatus.FAILED.value == "FAILED"


def test_scan_request_validation():
    """Verify folder_id cannot be empty or whitespace."""
    req = ScanRequest(folder_id="  abc123folder  ")
    assert req.folder_id == "abc123folder"

    with pytest.raises(ValidationError):
        ScanRequest(folder_id="   ")


def test_update_title_request_validation():
    """Verify title update validation."""
    req = UpdateTitleRequest(title="  New Video Title  ")
    assert req.title == "New Video Title"

    with pytest.raises(ValidationError):
        UpdateTitleRequest(title="")


def test_video_job_schema_youtube_url_computation():
    """Verify youtube_url computed property."""
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
