"""
NimbleVault – Async Database Engine & Session Factory
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# Normalize database URL for asyncpg / aiosqlite compatibility
_db_url = settings.DATABASE_URL
_engine_kwargs: dict = {"echo": settings.DEBUG}

if _db_url.startswith("sqlite"):
    if _db_url.startswith("sqlite://") and not _db_url.startswith("sqlite+aiosqlite://"):
        _db_url = _db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
else:
    if _db_url.startswith("postgresql://"):
        _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "sslmode=require" in _db_url:
        _db_url = _db_url.replace("sslmode=require", "ssl=require")
    if "&channel_binding=require" in _db_url:
        _db_url = _db_url.replace("&channel_binding=require", "")
    elif "channel_binding=require&" in _db_url:
        _db_url = _db_url.replace("channel_binding=require&", "")
    elif "?channel_binding=require" in _db_url:
        _db_url = _db_url.replace("?channel_binding=require", "")

    _engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    })

# ── Engine ─────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    _db_url,
    **_engine_kwargs,
)

# ── Session factory ────────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Base declarative class ─────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency helper ──────────────────────────────────────────────────────────
@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context-manager session for use inside background tasks."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
