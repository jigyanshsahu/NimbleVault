"""
NimbleVault – FastAPI Application Entry Point
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import Base, engine

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if get_settings().DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    # ── Startup ────────────────────────────────────────────────────────────────
    logger.info("NimbleVault starting up…")

    # Create tables if they don't exist (idempotent)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified / created.")

    # Ensure temp download directory exists
    tmp = settings.TEMP_DOWNLOAD_DIR
    os.makedirs(tmp, exist_ok=True)
    logger.info("Temp download dir: %s", tmp)

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────────
    logger.info("NimbleVault shutting down…")
    await engine.dispose()


# ── Application factory ────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Automated AI-powered video pipeline: "
        "Google Drive → Gemini title generation → YouTube upload"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(router)


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": settings.APP_NAME})
