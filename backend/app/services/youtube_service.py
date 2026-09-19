"""
NimbleVault – YouTube Service
Handles OAuth2 authentication and resumable video uploads.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path

import google.oauth2.credentials
import httpx
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Auth helpers ───────────────────────────────────────────────────────────────


def is_youtube_authenticated(token_path: str | None = None) -> bool:
    """Check whether a valid or refreshable YouTube OAuth token exists."""
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
    creds: google.oauth2.credentials.Credentials | None = None
    token_path = settings.YOUTUBE_TOKEN_JSON

    if os.path.exists(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                creds = google.oauth2.credentials.Credentials.from_authorized_user_info(
                    data, settings.YOUTUBE_SCOPES
                )
        except Exception as exc:
            logger.warning("Could not read YouTube token file '%s': %s", token_path, exc)
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _persist_token(creds)
        except Exception as exc:
            logger.warning("Failed to refresh YouTube token (%s): %s", type(exc).__name__, exc)
            creds = None

    if not creds or not creds.valid:
        if not allow_interactive:
            raise RuntimeError(
                "YouTube is not authenticated or the OAuth token has expired/revoked. "
                "Please run 'python scripts/auth_youtube.py' to authenticate your YouTube channel."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            settings.YOUTUBE_CLIENT_SECRETS_JSON,
            settings.YOUTUBE_SCOPES,
        )
        try:
            creds = flow.run_local_server(port=8080, open_browser=True)
        except Exception:
            creds = flow.run_local_server(port=0, open_browser=True)
        _persist_token(creds)

    return creds


def _persist_token(creds: google.oauth2.credentials.Credentials) -> None:
    token_path = Path(settings.YOUTUBE_TOKEN_JSON)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with open(token_path, "w", encoding="utf-8") as fh:
        fh.write(creds.to_json())
    logger.info("YouTube token persisted → %s", token_path)


def _build_youtube_service():  # type: ignore[return]
    creds = _load_or_refresh_credentials(allow_interactive=False)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


# ── Service ────────────────────────────────────────────────────────────────────


class YouTubeService:
    """
    Wraps the YouTube Data API v3 for resumable video uploads.
    """

    def __init__(self) -> None:
        try:
            self._service = _build_youtube_service()
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialize YouTube API service: {exc}. "
                "Run 'python scripts/auth_youtube.py' to configure authentication."
            ) from exc

    async def upload_video(
        self,
        file_path: Path,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
        category_id: str | None = None,
    ) -> str:
        """
        Resumably upload *file_path* to YouTube.

        Args:
            file_path: Local path to the video file.
            title: Title for the video (max 100 chars).
            description: Description for the video.
            tags: Optional list of tag strings.
            category_id: Optional YouTube numeric category ID string. Defaults to settings.YOUTUBE_VIDEO_CATEGORY_ID.

        Returns:
            The YouTube video ID (e.g. "dQw4w9WgXcQ").
        """
        resolved_category_id = category_id or settings.YOUTUBE_VIDEO_CATEGORY_ID
        return await asyncio.to_thread(
            self._upload_video_sync, file_path, title, description, tags or [], resolved_category_id
        )

    # ── Sync upload (runs in thread pool) ─────────────────────────────────────

    def _upload_video_sync(
        self,
        file_path: Path,
        title: str,
        description: str,
        tags: list[str],
        category_id: str = settings.YOUTUBE_VIDEO_CATEGORY_ID,
    ) -> str:
        body = {
            "snippet": {
                "title": title[:100],  # YouTube hard limit
                "description": description or f"Uploaded via NimbleVault – {file_path.name}",
                "tags": tags,
                "categoryId": category_id,
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
        max_retries = 5
        while response is None:
            retry_count = 0
            while True:
                try:
                    status, response = insert_request.next_chunk()
                    if status:
                        pct = int(status.progress() * 100)
                        logger.info("Uploading '%s' – %d%%", title, pct)
                    break
                except HttpError as http_err:
                    status_code = getattr(http_err.resp, "status", None)
                    err_content = str(http_err)
                    if status_code == 403 and "quotaExceeded" in err_content:
                        raise RuntimeError(
                            "YouTube API daily upload quota exceeded (403 quotaExceeded). "
                            "Default free tier quota is 10,000 units/day (video uploads cost 1,600 units). "
                            "Please test with --dry-run or wait for quota reset at midnight PST."
                        ) from http_err
                    if status_code == 401:
                        raise RuntimeError(
                            "YouTube authentication expired or invalid (401 Unauthorized). "
                            "Please run 'python scripts/auth_youtube.py' to re-authenticate."
                        ) from http_err

                    # For transient 5xx errors or 429 rate limits, retry with exponential backoff
                    if status_code in (429, 500, 502, 503, 504):
                        retry_count += 1
                        if retry_count > max_retries:
                            raise RuntimeError(
                                f"YouTube upload failed after {max_retries} retries: {http_err}"
                            ) from http_err
                        backoff = 2 ** retry_count
                        logger.warning(
                            "Transient HTTP %s during YouTube upload. Retrying in %ds (attempt %d/%d)...",
                            status_code, backoff, retry_count, max_retries
                        )
                        time.sleep(backoff)
                    else:
                        raise RuntimeError(f"YouTube API upload error: {http_err}") from http_err

                except (IOError, OSError) as io_err:
                    retry_count += 1
                    if retry_count > max_retries:
                        raise RuntimeError(
                            f"Network error during YouTube upload after {max_retries} retries: {io_err}"
                        ) from io_err
                    backoff = 2 ** retry_count
                    logger.warning(
                        "Network connection error during YouTube upload chunk. Retrying in %ds (attempt %d/%d)...",
                        backoff, retry_count, max_retries
                    )
                    time.sleep(backoff)

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
                or "This video is no longer available" in text
                or "This video has been removed for violating" in text
            )
            return not is_deleted
    except Exception as exc:
        logger.warning("Failed to check video availability for %s: %s", video_id, exc)
        # Default to True on network error to avoid false positive resets
        return True
