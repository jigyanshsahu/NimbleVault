"""
NimbleVault – SQLAlchemy ORM Model & Pydantic Schemas for VideoJob
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, String, Text, Index
from sqlalchemy.sql import func

from app.core.database import Base

# ── Status Enum ────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    TITLING = "TITLING"
    UPLOADING = "UPLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ── ORM Model ──────────────────────────────────────────────────────────────────

class VideoJob(Base):
    __tablename__ = "video_jobs"

    id: str = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    drive_file_id: str = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,          # prevents duplicate processing
        comment="Google Drive file ID – indexed to prevent duplicate scans",
    )
    file_name: str = Column(String(512), nullable=False)
    full_path: str = Column(Text, nullable=False)
    generated_title: str | None = Column(Text, nullable=True)
    youtube_video_id: str | None = Column(String(255), nullable=True)
    status: str = Column(
        String(20),
        nullable=False,
        default=JobStatus.PENDING.value,
    )
    error_log: str | None = Column(Text, nullable=True)
    created_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @property
    def youtube_url(self) -> str | None:
        if self.youtube_video_id:
            return f"https://www.youtube.com/watch?v={self.youtube_video_id}"
        return None

    # Composite index – common query pattern
    __table_args__ = (
        Index("ix_video_jobs_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<VideoJob id={self.id} status={self.status} file={self.file_name}>"


# ── Pydantic Schemas ───────────────────────────────────────────────────────────

from pydantic import BaseModel, ConfigDict, computed_field  # noqa: E402


class VideoJobSchema(BaseModel):
    """Read-only data validation and serialization schema for VideoJob."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    drive_file_id: str
    file_name: str
    full_path: str
    generated_title: str | None = None
    youtube_video_id: str | None = None
    status: str
    error_log: str | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def youtube_url(self) -> str | None:
        if self.youtube_video_id:
            return f"https://www.youtube.com/watch?v={self.youtube_video_id}"
        return None
