"""
NimbleVault – Google Drive Service
Handles recursive folder traversal and file streaming downloads.
"""
from __future__ import annotations

import asyncio
import io
import logging
import time
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Supported video extensions and MIME types
VIDEO_EXTENSIONS: set[str] = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".mpeg",
    ".mpg",
    ".webm",
    ".wmv",
    ".3gp",
    ".flv",
    ".m4v",
    ".ts",
    ".m2ts",
    ".mts",
    ".vob",
    ".ogv",
    ".m4p",
    ".f4v",
    ".asf",
    ".rm",
    ".rmvb",
    ".divx",
}


def is_video_file(name: str, mime: str) -> bool:
    """Check if a file is a video by MIME type or file extension."""
    if mime and mime.startswith("video/"):
        return True
    ext = Path(name).suffix.lower()
    return ext in VIDEO_EXTENSIONS

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
        Guards against cyclic structures and isolates subfolder permission errors.
        """
        return await asyncio.to_thread(
            self._list_videos_sync, folder_id, parent_path, set()
        )

    async def download_file(
        self,
        file_id: str,
        destination: Path,
    ) -> Path:
        """
        Stream-download a Drive file to *destination* using 8MB chunks with exponential backoff.
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
        visited_folder_ids: set[str] | None = None,
    ) -> list[DriveFile]:
        if visited_folder_ids is None:
            visited_folder_ids = set()

        if folder_id in visited_folder_ids:
            logger.warning("Cyclic folder reference detected for folder_id: %s (path: %s). Skipping.", folder_id, current_path)
            return []

        visited_folder_ids.add(folder_id)
        results: list[DriveFile] = []
        page_token: str | None = None

        while True:
            query = f"'{folder_id}' in parents and trashed = false"
            try:
                response = (
                    self._service.files()
                    .list(
                        q=query,
                        pageSize=1000,
                        fields="nextPageToken, files(id, name, mimeType, size, shortcutDetails)",
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True,
                    )
                    .execute()
                )
            except HttpError as exc:
                logger.error("Failed to query Google Drive folder '%s' (path: %s): %s", folder_id, current_path, exc)
                break

            for item in response.get("files", []):
                item_id: str = item["id"]
                item_name: str = item["name"]
                mime: str = item.get("mimeType", "")
                item_path = f"{current_path}/{item_name}"

                # Handle Google Drive shortcut references
                if mime == "application/vnd.google-apps.shortcut":
                    shortcut_details = item.get("shortcutDetails", {})
                    target_id = shortcut_details.get("targetId")
                    target_mime = shortcut_details.get("targetMimeType", "")
                    if target_id:
                        if target_mime == "application/vnd.google-apps.folder":
                            try:
                                sub_results = self._list_videos_sync(target_id, item_path, visited_folder_ids)
                                results.extend(sub_results)
                            except Exception as sub_exc:
                                logger.warning("Failed to inspect shortcut folder '%s': %s", item_path, sub_exc)
                        elif is_video_file(item_name, target_mime):
                            results.append(
                                DriveFile(
                                    file_id=target_id,
                                    file_name=item_name,
                                    mime_type=target_mime,
                                    full_path=item_path,
                                    size=int(item.get("size", 0)),
                                )
                            )
                    continue

                if mime == "application/vnd.google-apps.folder":
                    # Recurse into sub-folder with fault isolation
                    try:
                        sub_results = self._list_videos_sync(item_id, item_path, visited_folder_ids)
                        results.extend(sub_results)
                    except Exception as sub_exc:
                        logger.warning(
                            "Failed to inspect subfolder '%s' (%s): %s. Continuing traversal.",
                            item_path, item_id, sub_exc
                        )
                elif is_video_file(item_name, mime):
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

        max_retries = 5
        chunk_size = 8 * 1024 * 1024  # 8 MB chunks

        try:
            downloader = MediaIoBaseDownload(fh, request, chunksize=chunk_size)
            done = False
            while not done:
                retry_count = 0
                while True:
                    try:
                        status, done = downloader.next_chunk()
                        if status:
                            pct = int(status.progress() * 100)
                            logger.info("Downloading %s – %d%%", destination.name, pct)
                        break
                    except (HttpError, IOError, OSError) as exc:
                        retry_count += 1
                        if retry_count > max_retries:
                            raise RuntimeError(
                                f"Drive download failed for {file_id} after {max_retries} retries: {exc}"
                            ) from exc
                        backoff = 2 ** retry_count
                        logger.warning(
                            "Transient error downloading chunk (%s). Retrying in %ds (attempt %d/%d)...",
                            exc, backoff, retry_count, max_retries
                        )
                        time.sleep(backoff)
        except Exception as exc:
            fh.close()
            destination.unlink(missing_ok=True)
            raise RuntimeError(
                f"Drive download failed for {file_id}: {exc}"
            ) from exc
        finally:
            if not fh.closed:
                fh.close()

        logger.info("Download complete → %s", destination)
        return destination
