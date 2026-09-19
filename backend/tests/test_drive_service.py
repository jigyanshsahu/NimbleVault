"""
Unit tests for DriveService (Mass Content Acquisition).
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from app.services.drive_service import (
    DriveService,
    DriveFile,
    is_video_file,
    VIDEO_EXTENSIONS,
)


def test_is_video_file_by_extension():
    """Verify supported video file extensions are detected."""
    assert is_video_file("video.mp4", "application/octet-stream")
    assert is_video_file("clip.MOV", "")
    assert is_video_file("movie.avi", "")
    assert is_video_file("recording.mkv", "")
    assert is_video_file("web.webm", "")
    assert is_video_file("stream.flv", "")
    assert is_video_file("old.wmv", "")
    assert is_video_file("phone.3gp", "")

    assert not is_video_file("document.pdf", "application/pdf")
    assert not is_video_file("image.png", "image/png")
    assert not is_video_file("data.json", "application/json")
    assert not is_video_file("script.py", "text/x-python")


def test_is_video_file_by_mime_type():
    """Verify MIME types starting with video/ are accepted regardless of extension."""
    assert is_video_file("unknown_file", "video/mp4")
    assert is_video_file("custom.bin", "video/quicktime")
    assert is_video_file("blob", "video/avi")
    assert is_video_file("feed", "video/matroska")
    assert not is_video_file("file.txt", "text/plain")


@pytest.mark.asyncio
async def test_list_videos_recursive_mock():
    """Verify recursive directory traversal correctly handles nested subfolders."""
    mock_service = MagicMock()

    root_response = {
        "files": [
            {
                "id": "folder_sub1",
                "name": "sub1",
                "mimeType": "application/vnd.google-apps.folder",
            },
            {
                "id": "file_root_vid",
                "name": "root.mp4",
                "mimeType": "video/mp4",
                "size": "1048576",
            },
        ],
        "nextPageToken": None,
    }

    sub1_response = {
        "files": [
            {
                "id": "file_nested_vid",
                "name": "nested.mkv",
                "mimeType": "video/matroska",
                "size": "2097152",
            }
        ],
        "nextPageToken": None,
    }

    def list_side_effect(q, **kwargs):
        mock_req = MagicMock()
        if "'root_folder_id' in parents" in q:
            mock_req.execute.return_value = root_response
        elif "'folder_sub1' in parents" in q:
            mock_req.execute.return_value = sub1_response
        else:
            mock_req.execute.return_value = {"files": [], "nextPageToken": None}
        return mock_req

    mock_service.files().list.side_effect = list_side_effect

    with patch("app.services.drive_service._build_drive_service", return_value=mock_service):
        drive = DriveService()
        drive._service = mock_service

        results = await drive.list_videos_recursive("root_folder_id", parent_path="Drive")

        assert len(results) == 2
        paths = {f.full_path: f for f in results}

        assert "Drive/root.mp4" in paths
        assert paths["Drive/root.mp4"].size == 1048576

        assert "Drive/sub1/nested.mkv" in paths
        assert paths["Drive/sub1/nested.mkv"].size == 2097152


def test_is_video_file_additional_extensions():
    """Verify newly added video formats like .ts, .mts, .vob, .divx are detected."""
    assert is_video_file("stream.ts", "")
    assert is_video_file("avchd.mts", "")
    assert is_video_file("dvd.vob", "")
    assert is_video_file("movie.divx", "")
    assert is_video_file("clip.m4v", "")


@pytest.mark.asyncio
async def test_list_videos_recursive_shortcut_handling():
    """Verify shortcuts to folders and videos are resolved properly."""
    mock_service = MagicMock()

    root_response = {
        "files": [
            {
                "id": "shortcut_to_folder",
                "name": "shortcut_folder",
                "mimeType": "application/vnd.google-apps.shortcut",
                "shortcutDetails": {
                    "targetId": "target_folder_1",
                    "targetMimeType": "application/vnd.google-apps.folder",
                },
            },
            {
                "id": "shortcut_to_video",
                "name": "shared_lecture.mp4",
                "mimeType": "application/vnd.google-apps.shortcut",
                "size": "5000000",
                "shortcutDetails": {
                    "targetId": "target_video_file_1",
                    "targetMimeType": "video/mp4",
                },
            },
        ],
        "nextPageToken": None,
    }

    target_folder_response = {
        "files": [
            {
                "id": "nested_video_id",
                "name": "lecture_part2.mov",
                "mimeType": "video/quicktime",
                "size": "3000000",
            }
        ],
        "nextPageToken": None,
    }

    def list_side_effect(q, **kwargs):
        mock_req = MagicMock()
        if "'root_folder' in parents" in q:
            mock_req.execute.return_value = root_response
        elif "'target_folder_1' in parents" in q:
            mock_req.execute.return_value = target_folder_response
        else:
            mock_req.execute.return_value = {"files": [], "nextPageToken": None}
        return mock_req

    mock_service.files().list.side_effect = list_side_effect

    with patch("app.services.drive_service._build_drive_service", return_value=mock_service):
        drive = DriveService()
        drive._service = mock_service

        results = await drive.list_videos_recursive("root_folder", parent_path="Drive")

        assert len(results) == 2
        file_ids = {f.file_id for f in results}
        assert "target_video_file_1" in file_ids
        assert "nested_video_id" in file_ids
