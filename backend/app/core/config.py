"""
NimbleVault – Application Configuration
Loads all settings from environment variables via pydantic-settings.
"""
from __future__ import annotations

import os
import tempfile
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "NimbleVault"
    DEBUG: bool = False

    # ── Database ───────────────────────────────────────────────────────────────
    # Supports SQLite (zero-setup local execution) and PostgreSQL (production asyncpg)
    DATABASE_URL: str = "sqlite+aiosqlite:///nimblevault.db"

    # ── Google / Drive ─────────────────────────────────────────────────────────
    GOOGLE_SERVICE_ACCOUNT_JSON: str = "service_account.json"
    GOOGLE_DRIVE_SCOPES: list[str] = [
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    # ── YouTube ────────────────────────────────────────────────────────────────
    YOUTUBE_SCOPES: list[str] = [
        "https://www.googleapis.com/auth/youtube.upload",
    ]
    YOUTUBE_CLIENT_SECRETS_JSON: str = "client_secrets.json"
    YOUTUBE_TOKEN_JSON: str = "youtube_token.json"
    YOUTUBE_VIDEO_CATEGORY_ID: str = "22"   # "People & Blogs"
    YOUTUBE_PRIVACY_STATUS: str = "private"  # private | unlisted | public

    # ── Gemini ─────────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    # ── Local Storage ──────────────────────────────────────────────────────────
    TEMP_DOWNLOAD_DIR: str = os.path.join(tempfile.gettempdir(), "nimblevault_downloads")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
