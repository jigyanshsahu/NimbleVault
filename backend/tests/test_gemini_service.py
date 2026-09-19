"""
Unit tests for GeminiService (Intelligent Metadata Generation).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.gemini_service import GeminiService


def test_fallback_title_rubric_examples():
    """Verify fallback title logic derives clean titles matching rubric patterns."""
    cases = [
        ("Drive/Vlogs/2024/Week12/Final_Edit.mp4", "Vlogs: 2024 Week12 Final Edit"),
        ("Drive/Products/Launch_X/Tutorials/Getting_Started.mov", "Products: Launch X Tutorials Getting Started"),
        ("Drive/Team/Archive/Q3/Marketing_Review_10-05.avi", "Team: Archive Q3 Marketing Review 10 05"),
        ("Drive/Clients/ACME/Testimonial_v2.mp4", "Clients: Acme Testimonial (v2)"),
    ]

    for path, expected in cases:
        result = GeminiService._fallback_title(path)
        assert result == expected


def test_fallback_title_version_tag_extraction():
    """Ensure version tags like _v2, _v3 are extracted into (v2), (v3)."""
    assert GeminiService._fallback_title("Drive/Campaigns/Nike/Spot_v3.mp4") == "Campaigns: Nike Spot (v3)"
    assert GeminiService._fallback_title("Drive/Demos/Product_v1.mov") == "Demos: Product (v1)"


@pytest.mark.asyncio
async def test_generate_title_success():
    """Verify generate_title returns the AI generated title string."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"title": "Vlogs 2024: Week 12 Final Edit", "description": "Test description", "tags": ["Vlogs", "2024"], "category": "Entertainment"}'

    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch("google.genai.Client", return_value=mock_client):
        service = GeminiService()
        service._client = mock_client

        title = await service.generate_title("Drive/Vlogs/2024/Week12/Final_Edit.mp4")
        assert title == "Vlogs 2024: Week 12 Final Edit"


@pytest.mark.asyncio
async def test_generate_metadata_success():
    """Verify generate_metadata returns a complete VideoMetadata model."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"title": "Launch X Tutorial", "description": "Detailed walkthrough.", "tags": ["Tech", "Guide"], "category": "Education"}'

    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch("google.genai.Client", return_value=mock_client):
        service = GeminiService()
        service._client = mock_client

        meta = await service.generate_metadata("Drive/Products/Launch_X/Tutorials/Getting_Started.mov")
        assert meta.title == "Launch X Tutorial"
        assert meta.description == "Detailed walkthrough."
        assert meta.tags == ["Tech", "Guide"]
        assert meta.category == "Education"


@pytest.mark.asyncio
async def test_generate_title_fallback_on_api_error():
    """Verify generate_title falls back gracefully to deterministic logic on API errors."""
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=Exception("503 Server Unavailable"))

    with patch("google.genai.Client", return_value=mock_client):
        service = GeminiService()
        service._client = mock_client

        title = await service.generate_title("Drive/Clients/ACME/Testimonial_v2.mp4")
        # Should gracefully fall back without raising an unhandled exception
        assert title == "Clients: Acme Testimonial (v2)"
