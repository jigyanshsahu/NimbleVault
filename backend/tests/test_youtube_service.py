"""
Unit tests for YouTubeService (Seamless Distribution).
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from app.services.youtube_service import YouTubeService, is_youtube_authenticated


def test_is_youtube_authenticated_missing_file(tmp_path):
    """Ensure is_youtube_authenticated returns False when token file is absent."""
    non_existent = str(tmp_path / "non_existent.json")
    assert not is_youtube_authenticated(token_path=non_existent)


@pytest.mark.asyncio
async def test_upload_video_mock(tmp_path):
    """Verify upload_video constructs proper metadata and calls insert."""
    mock_service = MagicMock()
    mock_request = MagicMock()
    mock_request.next_chunk.return_value = (None, {"id": "test_video_12345"})
    mock_service.videos().insert.return_value = mock_request

    dummy_file = tmp_path / "test.mp4"
    dummy_file.write_bytes(b"dummy video content")

    with patch("app.services.youtube_service._build_youtube_service", return_value=mock_service):
        service = YouTubeService()
        service._service = mock_service

        video_id = await service.upload_video(
            file_path=dummy_file,
            title="A" * 150,  # Long title to test truncation
            description="Test description",
            tags=["test", "tag"],
        )

        assert video_id == "test_video_12345"
        # Verify title was truncated to <= 100 characters per YouTube API rules
        insert_kwargs = mock_service.videos().insert.call_args[1]
        inserted_title = insert_kwargs["body"]["snippet"]["title"]
        assert len(inserted_title) <= 100


def test_is_video_alive_on_youtube_mock_and_empty():
    """Verify mock and empty IDs are treated as alive to avoid false resets."""
    from app.services.youtube_service import is_video_alive_on_youtube

    assert is_video_alive_on_youtube("") is True
    assert is_video_alive_on_youtube(None) is True
    assert is_video_alive_on_youtube("mock_12345") is True


def test_is_video_alive_on_youtube_active():
    """Verify active video returns True when uploader removal string is absent."""
    from app.services.youtube_service import is_video_alive_on_youtube

    mock_resp = MagicMock()
    mock_resp.text = "<html><head><title>My Awesome Video - YouTube</title></head><body>Player content</body></html>"

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        assert is_video_alive_on_youtube("real_active_video_id") is True


def test_is_video_alive_on_youtube_deleted():
    """Verify deleted video returns False when removal message is present."""
    from app.services.youtube_service import is_video_alive_on_youtube

    mock_resp = MagicMock()
    mock_resp.text = "<html><body>This video has been removed by the uploader</body></html>"

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        assert is_video_alive_on_youtube("deleted_video_id") is False

