"""
Unit tests for GeminiService (Intelligent Metadata Generation).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.gemini_service import GeminiService


def test_fallback_title_rubric_examples():
    """Verify fallback title logic derives clean titles matching rubric patterns from PDF page 2."""
    cases = [
        ("Drive/Vlogs/2024/Week12/Final_Edit.mp4", "Vlogs 2024: Week 12 Final Edit"),
        ("Drive/Products/Launch_X/Tutorials/Getting_Started.mov", "Launch X Product Tutorial: Getting Started"),
        ("Drive/Team/Archive/Q3/Marketing_Review_10-05.avi", "Team Archive Q3: Marketing Review 10-05"),
        ("Drive/Clients/ACME/Testimonial_v2.mp4", "Client Testimonial: ACME (v2)"),
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
    """Verify generate_metadata returns a complete VideoMetadata model with strict JSON."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        '{"title": "Launch X Product Tutorial: Getting Started", '
        '"description": "Learn the essential first steps with Launch X. Perfect for beginners to master the basics quickly.\\n\\n#Products #LaunchX #Tutorials"}'
    )

    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch("google.genai.Client", return_value=mock_client):
        service = GeminiService()
        service._client = mock_client

        meta = await service.generate_metadata("Drive/Products/Launch_X/Tutorials/Getting_Started.mov")
        assert meta.title == "Launch X Product Tutorial: Getting Started"
        assert "Learn the essential first steps" in meta.description
        assert "LaunchX" in meta.tags
        assert len(meta.tags) == 3
        assert set(meta.model_dump().keys()) == {"title", "description"}


def test_metadata_strict_json_keys_and_hashtag_extraction():
    """Verify VideoMetadata model strictly serializes only 'title' and 'description' keys."""
    from app.services.gemini_service import VideoMetadata

    meta = VideoMetadata(
        title="Vlogs 2024: Week 12 Final Edit",
        description="Welcome to the latest vlog update for Week 12. Follow our journey this season.\n\n#Vlogs #2024 #Week12 #FinalEdit",
    )
    dump = meta.model_dump()
    assert set(dump.keys()) == {"title", "description"}
    assert dump["title"] == "Vlogs 2024: Week 12 Final Edit"
    assert "Vlogs" in meta.tags
    assert "Week12" in meta.tags
    assert len(meta.tags) == 4


@pytest.mark.asyncio
async def test_generate_title_fallback_on_api_error():
    """Verify generate_title falls back gracefully to deterministic logic on API errors."""
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(side_effect=Exception("503 Server Unavailable"))

    with patch("google.genai.Client", return_value=mock_client):
        service = GeminiService()
        service._client = mock_client

        title = await service.generate_title("Drive/Clients/ACME/Testimonial_v2.mp4")
        assert title == "Client Testimonial: ACME (v2)"
