"""
NimbleVault – Google Drive Service
Handles recursive folder traversal and file streaming downloads.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
from pathlib import Path
from typing import AsyncGenerator

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# MIME types we care about
VIDEO_MIME_TYPES: set[str] = {
    "video/mp4",
    "video/quicktime",          # .mov
    "video/x-msvideo",         # .avi
    "video/x-matroska",        # .mkv
    "video/mpeg",
    "video/webm",
    "video/x-ms-wmv",
    "video/3gpp",
}

# ── DriveFile dataclass ────────────────────────────────────────────────────────

from dataclasses import dataclass


@dataclass
class DriveFile:
    file_id: str
    file_name: str
    mime_type: str
    full_path: str   # e.g. "Drive/Vlogs/2024/Week12/Final_Edit.mp4"
    size: int        # bytes


# ── Service builder ────────────────────────────────────────────────────────────

def _build_drive_service():  # type: ignore[return]
    """Builds an authenticated Google Drive API v3 service object."""
    credentials = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_JSON,
        scopes=settings.GOOGLE_DRIVE_SCOPES,
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


# ── Core recursive traversal ───────────────────────────────────────────────────

class DriveService:
    """
    Wraps Google Drive API v3 for recursive folder scanning and
    chunked file downloads.
    """

    def __init__(self) -> None:
        self._service = _build_drive_service()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def list_videos_recursive(
        self,
        folder_id: str,
        parent_path: str = "Drive",
    ) -> list[DriveFile]:
        """
        Recursively walk *folder_id* and every sub-folder, collecting
        all video files along with their virtual Drive path string.
        """
        return await asyncio.to_thread(
            self._list_videos_sync, folder_id, parent_path
        )

    async def download_file(
        self,
        file_id: str,
        destination: Path,
    ) -> Path:
        """
        Stream-download a Drive file to *destination*.
        Returns the destination path on success.
        """
        return await asyncio.to_thread(
            self._download_file_sync, file_id, destination
        )

    # ── Sync internals (run in thread pool) ───────────────────────────────────

    def _list_videos_sync(
        self,
        folder_id: str,
        current_path: str,
    ) -> list[DriveFile]:
        results: list[DriveFile] = []
        page_token: str | None = None

        while True:
            query = f"'{folder_id}' in parents and trashed = false"
            response = (
                self._service.files()
                .list(
                    q=query,
                    pageSize=200,
                    fields="nextPageToken, files(id, name, mimeType, size)",
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )

            for item in response.get("files", []):
                item_id: str = item["id"]
                item_name: str = item["name"]
                mime: str = item.get("mimeType", "")
                item_path = f"{current_path}/{item_name}"

                if mime == "application/vnd.google-apps.folder":
                    # Recurse into sub-folder
                    results.extend(
                        self._list_videos_sync(item_id, item_path)
                    )
                elif mime in VIDEO_MIME_TYPES:
                    results.append(
                        DriveFile(
                            file_id=item_id,
                            file_name=item_name,
                            mime_type=mime,
                            full_path=item_path,
                            size=int(item.get("size", 0)),
                        )
                    )

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return results

    def _download_file_sync(
        self,
        file_id: str,
        destination: Path,
    ) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)

        request = self._service.files().get_media(fileId=file_id, supportsAllDrives=True)
        fh = io.FileIO(str(destination), "wb")

        try:
            downloader = MediaIoBaseDownload(fh, request, chunksize=8 * 1024 * 1024)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    logger.info(
                        "Downloading %s – %d%%", destination.name, pct
                    )
        except HttpError as exc:
            fh.close()
            destination.unlink(missing_ok=True)
            raise RuntimeError(
                f"Drive download failed for {file_id}: {exc}"
            ) from exc
        finally:
            fh.close()

        logger.info("Download complete → %s", destination)
        return destination
