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

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Prompt template ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a YouTube content strategist specialising in title optimisation.
Your task is to convert a Google Drive file path into a clean, professional
YouTube video title. Return ONLY the final title string — no explanations,
no quotation marks, no markdown.

Transformation rules:
1. Strip the leading "Drive/" prefix and the file extension.
2. Replace underscores and hyphens with spaces.
3. Capitalise each meaningful word (title case).
4. Identify the primary category from the second path segment and use it
   as the prefix separated by a colon.
5. If there is a version tag (e.g. _v2, _v3) move it to the end in
   parentheses: "(v2)".
6. For date-like segments (e.g. Q3, Week12, 2024) keep them in the title
   naturally.

Examples:
  Drive/Vlogs/2024/Week12/Final_Edit.mp4
  → Vlogs 2024: Week 12 Final Edit

  Drive/Products/Launch_X/Tutorials/Getting_Started.mov
  → Launch X Product Tutorial: Getting Started

  Drive/Team/Archive/Q3/Marketing_Review_10-05.avi
  → Team Archive Q3: Marketing Review 10-05

  Drive/Clients/ACME/Testimonial_v2.mp4
  → Client Testimonial: ACME (v2)
"""

# ── Service ────────────────────────────────────────────────────────────────────


class GeminiService:
    """Wraps the google-genai SDK to generate YouTube titles from Drive paths."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def generate_title(self, full_path: str) -> str:
        """
        Asynchronously generate a YouTube title from a Drive path string.

        Args:
            full_path: Virtual Drive path, e.g. "Drive/Vlogs/2024/Week12/Final_Edit.mp4"

        Returns:
            A clean, professionally formatted title string.
        """
        prompt = (
            f"Convert this Drive path to a YouTube title:\n{full_path}"
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    temperature=0.3,
                    max_output_tokens=128,
                ),
            )
            title = response.text.strip().strip('"').strip("'")
            logger.info("Gemini title for '%s' → '%s'", full_path, title)
            return title

        except Exception as exc:
            logger.error("Gemini API error for path '%s': %s", full_path, exc)
            # Graceful fallback: derive a reasonable title from the path
            return self._fallback_title(full_path)

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
