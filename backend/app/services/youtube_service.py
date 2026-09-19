"""
NimbleVault – YouTube Service
Handles OAuth2 authentication and resumable video uploads.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import google.oauth2.credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Auth helpers ───────────────────────────────────────────────────────────────


def is_youtube_authenticated(token_path: str | None = None) -> bool:
    """Check whether a valid or refreshable YouTube OAuth token exists."""
    import os
    import json

    target_path = token_path or get_settings().YOUTUBE_TOKEN_JSON
    if not os.path.exists(target_path):
        return False
    try:
        with open(target_path) as fh:
            creds = google.oauth2.credentials.Credentials.from_authorized_user_info(
                json.load(fh), settings.YOUTUBE_SCOPES
            )
            return bool(creds and (creds.valid or creds.refresh_token))
    except Exception:
        return False


def _load_or_refresh_credentials(allow_interactive: bool = False) -> google.oauth2.credentials.Credentials:
    """
    Load OAuth2 credentials from the token file, refreshing if expired.
    If allow_interactive is True and token is missing, starts local browser OAuth flow.
    """
    import json
    import os

    creds: google.oauth2.credentials.Credentials | None = None
    token_path = settings.YOUTUBE_TOKEN_JSON

    if os.path.exists(token_path):
        with open(token_path) as fh:
            creds = google.oauth2.credentials.Credentials.from_authorized_user_info(
                json.load(fh), settings.YOUTUBE_SCOPES
            )

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _persist_token(creds)
        except Exception as exc:
            logger.warning("Failed to refresh YouTube token: %s", exc)
            creds = None

    if not creds or not creds.valid:
        if not allow_interactive:
            raise RuntimeError(
                "YouTube is not authenticated. Please run 'python scripts/auth_youtube.py' "
                "to authenticate your YouTube account."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            settings.YOUTUBE_CLIENT_SECRETS_JSON,
            settings.YOUTUBE_SCOPES,
        )
        creds = flow.run_local_server(port=8080, open_browser=True)
        _persist_token(creds)

    return creds


def _persist_token(creds: google.oauth2.credentials.Credentials) -> None:
    import json

    with open(settings.YOUTUBE_TOKEN_JSON, "w") as fh:
        fh.write(creds.to_json())
    logger.info("YouTube token persisted → %s", settings.YOUTUBE_TOKEN_JSON)


def _build_youtube_service():  # type: ignore[return]
    creds = _load_or_refresh_credentials(allow_interactive=False)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


# ── Service ────────────────────────────────────────────────────────────────────


class YouTubeService:
    """
    Wraps the YouTube Data API v3 for resumable video uploads.
    """

    def __init__(self) -> None:
        self._service = _build_youtube_service()

    async def upload_video(
        self,
        file_path: Path,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
    ) -> str:
        """
        Resumably upload *file_path* to YouTube.

        Returns:
            The YouTube video ID (e.g. "dQw4w9WgXcQ").
        """
        return await asyncio.to_thread(
            self._upload_video_sync, file_path, title, description, tags or []
        )

    # ── Sync upload (runs in thread pool) ─────────────────────────────────────

    def _upload_video_sync(
        self,
        file_path: Path,
        title: str,
        description: str,
        tags: list[str],
    ) -> str:
        body = {
            "snippet": {
                "title": title[:100],  # YouTube hard limit
                "description": description or f"Uploaded via NimbleVault – {file_path.name}",
                "tags": tags,
                "categoryId": settings.YOUTUBE_VIDEO_CATEGORY_ID,
            },
            "status": {
                "privacyStatus": settings.YOUTUBE_PRIVACY_STATUS,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(file_path),
            chunksize=8 * 1024 * 1024,  # 8 MB chunks
            resumable=True,
        )

        insert_request = self._service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = insert_request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                logger.info("Uploading '%s' – %d%%", title, pct)

        video_id: str = response["id"]
        logger.info(
            "Upload complete: https://www.youtube.com/watch?v=%s", video_id
        )
        return video_id


def is_video_alive_on_youtube(video_id: str) -> bool:
    """
    Check if a video still exists and is accessible on YouTube.
    Detects whether the video was deleted or removed by the uploader.
    """
    import httpx

    if not video_id or video_id.startswith("mock_"):
        return True

    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            resp = client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            text = resp.text
            is_deleted = (
                "This video has been removed by the uploader" in text
                or "This video does not exist" in text
            )
            return not is_deleted
    except Exception as exc:
        logger.warning("Failed to check video availability for %s: %s", video_id, exc)
        # Default to True on network error to avoid false positive resets
        return True
