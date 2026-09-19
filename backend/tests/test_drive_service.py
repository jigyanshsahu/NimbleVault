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

    # Non-video files
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

    # Root folder contains one subfolder 'sub1' and one video 'root.mp4'
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

    # 'sub1' folder contains a nested video 'nested.mkv'
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
