"""
NimbleVault – Gemini Service
Generates professionally formatted YouTube titles from Drive file paths.
"""
from __future__ import annotations

import logging
import re

from google import genai
from google.genai import types

from app.core.config import get_settings

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Structured Metadata Schema ─────────────────────────────────────────────────

class VideoMetadata(BaseModel):
    title: str = Field(description="Clean, engaging, professionally formatted YouTube title")
    description: str = Field(description="Contextual 2-paragraph YouTube description based on the route context")
    tags: list[str] = Field(description="5 to 8 relevant SEO search tags")
    category: str = Field(description="Primary category name (e.g. Technology, Education, Entertainment)")


# ── Prompt template ────────────────────────────────────────────────────────────

_METADATA_SYSTEM_PROMPT = """\
You are a YouTube content strategist and metadata optimization engine.
Given a Google Drive file path (file route), generate comprehensive, discoverable YouTube metadata:

1. title: Clean, professional heading following these pattern rules:
   - Identify primary category/topic from path segments.
   - Convert snake_case/hyphens to Title Case.
   - Format version tags as (v2), (v3) at the end.
   - Keep dates/quarters like 2024, Week 12, Q3 intact.
   Examples:
   - Drive/Vlogs/2024/Week12/Final_Edit.mp4 -> Vlogs 2024: Week 12 Final Edit
   - Drive/Products/Launch_X/Tutorials/Getting_Started.mov -> Launch X Product Tutorial: Getting Started
   - Drive/Team/Archive/Q3/Marketing_Review_10-05.avi -> Team Archive Q3: Marketing Review 10-05
   - Drive/Clients/ACME/Testimonial_v2.mp4 -> Client Testimonial: ACME (v2)

2. description: An engaging 2-paragraph YouTube description detailing the content, the series/archive context, and viewer takeaways.
3. tags: 5 to 8 relevant SEO keywords and search tags.
4. category: High-level category name (e.g. Education, Technology, People & Blogs, Entertainment).
"""


# ── Service ────────────────────────────────────────────────────────────────────


class GeminiService:
    """Wraps the google-genai SDK to generate YouTube metadata from Drive paths."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def generate_metadata(self, full_path: str) -> VideoMetadata:
        """
        Asynchronously generate full YouTube metadata (title, description, tags, category)
        from a Google Drive file route.
        """
        prompt = f"Google Drive File Route: {full_path}"

        try:
            response = await self._client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_METADATA_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=VideoMetadata,
                    temperature=0.1,
                    max_output_tokens=1024,
                ),
            )
            raw_text = (response.text or "").strip()
            if not raw_text:
                logger.warning("Gemini returned empty metadata for '%s', using fallback", full_path)
                return self._fallback_metadata(full_path)

            metadata = VideoMetadata.model_validate_json(raw_text)
            logger.info("Gemini metadata generated for '%s' → Title: '%s'", full_path, metadata.title)
            return metadata

        except Exception as exc:
            logger.error("Gemini API error for path '%s' (%s), using fallback: %s", full_path, type(exc).__name__, exc)
            return self._fallback_metadata(full_path)

    async def generate_title(self, full_path: str) -> str:
        """
        Generate a title string (backward-compatible convenience wrapper).
        """
        meta = await self.generate_metadata(full_path)
        return meta.title

    # ── Fallback ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fallback_title(full_path: str) -> str:
        """
        Best-effort title derived locally when the Gemini API is unavailable.
        Mirrors the same transformation rules applied in the prompt.
        """
        # Remove "Drive/" prefix and extension
        path = re.sub(r"^Drive/", "", full_path)
        path = re.sub(r"\.[^/]+$", "", path)

        segments = path.split("/")
        if not segments:
            return full_path

        # Identify category (first segment)
        category = segments[0].replace("_", " ").replace("-", " ")

        # Remaining segments become the body
        body_parts = segments[1:]
        body = " ".join(body_parts).replace("_", " ").replace("-", " ")

        # Version tag extraction  (v2, v3 …)
        version_match = re.search(r"\b(v\d+)\b", body, re.IGNORECASE)
        version_suffix = ""
        if version_match:
            version_suffix = f" ({version_match.group(1)})"
            body = body[: version_match.start()].strip()

        # Title-case everything
        category = category.title()
        body = body.title()

        title = f"{category}: {body}{version_suffix}" if body else category
        return title

    @classmethod
    def _fallback_metadata(cls, full_path: str) -> VideoMetadata:
        """
        Derive full fallback metadata locally when Gemini API is unreachable.
        """
        title = cls._fallback_title(full_path)
        
        # Extract segments for tags
        clean = re.sub(r"^Drive/", "", full_path)
        clean = re.sub(r"\.[^/]+$", "", clean)
        parts = [p.replace("_", " ").replace("-", " ").title() for p in clean.split("/") if p]
        
        category = parts[0] if parts else "General"
        tags = list(dict.fromkeys(["NimbleVault", category] + parts))[:8]
        
        description = (
            f"Automated upload via NimbleVault.\n\n"
            f"Title: {title}\n"
            f"Source Route: {full_path}\n"
            f"Category: {category}\n\n"
            f"This content was ingested, processed, and distributed automatically."
        )
        
        return VideoMetadata(
            title=title,
            description=description,
            tags=tags,
            category=category,
        )
