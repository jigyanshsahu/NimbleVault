<p align="center">
  <h1 align="center">🏛️ NimbleVault</h1>
  <p align="center">
    <strong>AI-Powered Video Content Automation Pipeline</strong>
  </p>
  <p align="center">
    <em>Automated ingestion from Google Drive · Intelligent metadata generation via Gemini AI · Seamless distribution to YouTube</em>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.10+-blue?logo=python&logoColor=white" alt="Python 3.10+" />
    <img src="https://img.shields.io/badge/database-SQLite-07405E?logo=sqlite&logoColor=white" alt="SQLite" />
    <img src="https://img.shields.io/badge/AI-Gemini_API-4285F4?logo=google&logoColor=white" alt="Gemini API" />
    <img src="https://img.shields.io/badge/YouTube-Data_API_v3-FF0000?logo=youtube&logoColor=white" alt="YouTube API" />
    <img src="https://img.shields.io/badge/Google_Drive-API_v3-34A853?logo=googledrive&logoColor=white" alt="Google Drive API" />
    <img src="https://img.shields.io/badge/async-aiosqlite-green" alt="Async" />
    <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License" />
  </p>
</p>

---

## 📑 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Google API Setup](#google-api-setup)
  - [Gemini API](#1-gemini-api)
  - [Google Drive API](#2-google-drive-api)
  - [YouTube Data API v3](#3-youtube-data-api-v3)
- [YouTube Authentication](#youtube-authentication)
- [Running the Application](#running-the-application)
  - [Demo Mode (Zero Credentials)](#1-demo-mode-zero-credentials)
  - [Status Check](#2-status-check)
  - [Dry Run](#3-dry-run)
  - [Live Pipeline](#4-live-pipeline)
  - [Additional Modes](#additional-modes)
- [Pipeline Workflow](#pipeline-workflow)
- [Database & State Management](#database--state-management)
- [AI Metadata Generation](#ai-metadata-generation)
- [Reliability & Error Handling](#reliability--error-handling)
- [Design Decisions & Rationale](#design-decisions--rationale)
- [Performance Considerations](#performance-considerations)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Quick Reference: CLI Commands](#quick-reference-cli-commands)
- [Reviewer Quick Start](#-reviewer-quick-start)

---

## Overview

NimbleVault is a Python-based backend automation platform that processes video files stored in Google Drive and publishes them to YouTube with AI-generated metadata. The system orchestrates four Google ecosystem services — **Google Drive**, **Google Gemini AI**, **YouTube Data API v3**, and **SQLite** — into a cohesive, fault-tolerant content pipeline.

```
  ┌──────────────┐         ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
  │ Google Drive  │────────▶│  NimbleVault │────────▶│  Gemini AI   │────────▶│   YouTube    │
  │              │ Discover │   Engine     │ Generate│  Metadata    │ Upload  │   Channel    │
  │  Video Files │ & Download│             │  Title  │              │  Video  │              │
  └──────────────┘         │  ┌────────┐  │         └──────────────┘         └──────────────┘
                           │  │ SQLite │  │
                           │  │  Jobs  │  │
                           │  └────────┘  │
                           └──────────────┘
```

> **Design Philosophy:** NimbleVault is intentionally built as a **backend automation engine and CLI** — not a web application. This keeps the execution environment lightweight and makes the pipeline suitable for local execution, scheduled cron jobs, CI/CD integration, and command-line workflows.

---

## Key Features

### 📁 Google Drive Integration
| Capability | Description |
|---|---|
| **Recursive Traversal** | Walks nested Google Drive folder hierarchies to discover all video assets |
| **Broad Format Support** | Detects 20+ video formats (`.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.wmv`, `.3gp`, `.flv`, etc.) via MIME type + extension matching |
| **Shortcut Resolution** | Follows Google Drive shortcut references to target folders and files |
| **Cycle Detection** | Guards against circular folder references using a visited-set algorithm |
| **Paginated API Calls** | Handles large folders using Drive API pagination (`nextPageToken`) |
| **Chunked Downloads** | Streams files in 8 MB chunks with dynamic single-line progress bars (speed, ETA, byte counters) to avoid loading entire videos into memory |
| **Fault-Isolated Traversal** | Subfolder permission errors are logged and skipped — they don't halt the entire scan |
| **Service Account Auth** | Uses a Google Service Account for secure, non-interactive Drive access |

### 🤖 AI Metadata Generation
| Capability | Description |
|---|---|
| **Contextual Titling** | Derives professional YouTube titles from the full Google Drive folder path hierarchy |
| **Rich Descriptions** | Generates 2–3 sentence descriptions with 3–5 relevant SEO hashtags |
| **Category Detection** | Dynamically selects the best-matching YouTube category ID from folder/file context |
| **Structured Output** | Uses Pydantic schema validation + `response_schema` to enforce strict JSON responses from Gemini |
| **Deterministic Fallback** | A complete offline metadata engine activates when Gemini is unavailable, rate-limited, or not configured — the pipeline never depends exclusively on the external AI service |

### 📺 YouTube Uploading
| Capability | Description |
|---|---|
| **OAuth 2.0 Authentication** | Interactive browser-based auth flow with persistent, auto-refreshable tokens |
| **Resumable Uploads** | Uses YouTube's resumable upload protocol for reliable large-file transfers |
| **Chunked Transmission** | Uploads in 8 MB chunks with dynamic single-line progress tracking |
| **Exponential Backoff Retry** | Handles transient 429/5xx errors with automatic exponential backoff (up to 5 retries) |
| **Quota-Aware Errors** | Detects `403 quotaExceeded` and provides actionable guidance |
| **Video Liveness Check** | Verifies if a previously uploaded video still exists on YouTube via HTTP scraping |
| **Configurable Privacy** | Supports `private`, `unlisted`, and `public` upload modes |

### 💾 Persistent State Tracking
| Capability | Description |
|---|---|
| **SQLite + aiosqlite** | Zero-setup, async-compatible local database — no server required |
| **Duplicate Prevention** | Unique index on `drive_file_id` prevents re-processing of known files |
| **State Machine** | Tracks each video through `PENDING → DOWNLOADING → TITLING → UPLOADING → COMPLETED` (or `FAILED`) |
| **Failure Tracking** | Records error logs per job for post-mortem debugging |
| **Self-Healing Reconciliation** | If a YouTube video is deleted, the system automatically resets the job to `PENDING` for re-upload |
| **Composite Index** | `(status, created_at)` index optimizes the most common query pattern |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Google Drive                                │
│                                                                     │
│       Nested folders containing video files (.mp4, .mov, ...)       │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 │  1. Recursive discovery (paginated, cycle-safe)
                                 │  2. Chunked download (8 MB segments)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       NimbleVault Engine                             │
│                                                                     │
│   ┌───────────────────┐  ┌───────────────────┐  ┌────────────────┐ │
│   │  drive_service.py │  │ gemini_service.py │  │ youtube_service│ │
│   │                   │  │                   │  │     .py        │ │
│   │ • Recursive scan  │  │ • AI title gen    │  │ • OAuth 2.0    │ │
│   │ • Shortcut follow │  │ • Description gen │  │ • Resumable    │ │
│   │ • Cycle detection │  │ • Category detect │  │   upload       │ │
│   │ • Chunked I/O     │  │ • Pydantic schema │  │ • Retry logic  │ │
│   │ • Fault isolation │  │ • Offline fallback│  │ • Liveness chk │ │
│   └────────┬──────────┘  └────────┬──────────┘  └───────┬────────┘ │
│            │                      │                      │          │
│            └──────────────────────┼──────────────────────┘          │
│                                   │                                 │
│                      ┌────────────▼────────────┐                    │
│                      │    SQLite Database       │                    │
│                      │                          │                    │
│                      │  • VideoJob ORM model    │                    │
│                      │  • Pydantic schemas      │                    │
│                      │  • State machine enum    │                    │
│                      │  • Async session mgmt    │                    │
│                      └──────────────────────────┘                    │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    Core Infrastructure                       │   │
│   │                                                             │   │
│   │  config.py (pydantic-settings)     database.py (SQLAlchemy) │   │
│   │  • Env-driven configuration        • Async engine/session   │   │
│   │  • Type-safe settings              • Context manager        │   │
│   │  • LRU-cached singleton            • Auto-commit/rollback   │   │
│   └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 │  3. Resumable upload (8 MB chunks)
                                 │  4. Exponential backoff retry
                                 ▼
                        ┌──────────────────┐
                        │     YouTube      │
                        │     Channel      │
                        └──────────────────┘
```

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.10+ | Core runtime with async/await and modern type hints |
| **Configuration** | pydantic-settings ≥ 2.3 | Type-safe, env-driven settings with validation |
| **ORM** | SQLAlchemy 2.0+ (async) | Declarative ORM models with async session management |
| **Database** | SQLite via aiosqlite ≥ 0.20 | Zero-setup, async-compatible embedded database |
| **AI Engine** | Google Gemini API (google-genai ≥ 1.0) | Structured metadata generation with schema enforcement |
| **Cloud Storage** | Google Drive API v3 | Recursive folder traversal and chunked file downloads |
| **Video Platform** | YouTube Data API v3 | Resumable video uploads with OAuth 2.0 |
| **Drive Auth** | Google Service Account | Non-interactive, credential-file-based authentication |
| **YouTube Auth** | OAuth 2.0 (google-auth-oauthlib) | Interactive browser flow with persistent token refresh |
| **HTTP Client** | httpx ≥ 0.27 | Video liveness checks via YouTube page scraping |
| **Progress Bar** | tqdm ≥ 4.66 | Dynamic transfer progress tracking (speed, ETA, byte counters, middle-truncated names) |
| **Env Loading** | python-dotenv ≥ 1.0 | `.env` file parsing for local development |

---

## Project Structure

```
nimblevault/
│
├── README.md                           # This file
├── .gitignore                          # Excludes secrets, venvs, caches, media files
│
└── backend/
    │
    ├── app/
    │   ├── __init__.py
    │   │
    │   ├── core/
    │   │   ├── config.py               # pydantic-settings: all env vars, LRU-cached singleton
    │   │   ├── database.py             # SQLAlchemy async engine, session factory, Base class
    │   │   └── progress.py             # TransferProgressBar: dynamic tqdm & fallback transfer progress
    │   │
    │   ├── models/
    │   │   └── video.py                # VideoJob ORM model, JobStatus enum, Pydantic schema
    │   │
    │   └── services/
    │       ├── drive_service.py        # DriveService: recursive scan, chunked download, cycle guard
    │       ├── gemini_service.py       # GeminiService: AI metadata gen, Pydantic schema, fallback engine
    │       └── youtube_service.py      # YouTubeService: OAuth2, resumable upload, retry, liveness
    │
    ├── scripts/
    │   ├── run_pipeline.py             # Main CLI entry point (all pipeline modes)
    │   ├── demo.py                     # Zero-credential reviewer demonstration
    │   ├── auth_youtube.py             # YouTube OAuth2 interactive authentication helper
    │   └── generate_metadata.py        # Standalone metadata generation utility
    │
    ├── tests/
    │   └── test_progress.py            # Unit tests for progress bar & transfer mechanics
    │
    ├── requirements.txt                # Pinned Python dependencies
    ├── .env.example                    # Environment variable template (safe to commit)
    ├── .env                            # Actual environment variables (DO NOT commit)
    ├── service_account.json            # Google Drive Service Account key (DO NOT commit)
    ├── client_secrets.json             # YouTube OAuth2 client credentials (DO NOT commit)
    └── youtube_token.json              # Persisted YouTube OAuth2 token (DO NOT commit)
```

> **⚠️ Security Note:** Files marked "DO NOT commit" contain sensitive credentials. They are excluded via [`.gitignore`](.gitignore). See [Security Considerations](#security-considerations) for details.

---

## Getting Started

### Prerequisites

| Requirement | Details |
|---|---|
| **Python** | 3.10 or newer |
| **Git** | For cloning the repository |
| **Google Account** | Required for all Google API integrations |
| **Google Cloud Project** | Required for Drive API, YouTube API, and Gemini API credentials |
| **Google Drive Folder** | A shared folder containing the videos to process |
| **YouTube Channel** | The target channel for live uploads |
| **Gemini API Key** | For AI-generated metadata (optional — deterministic fallback available) |

> **💡 Tip:** The [demo mode](#1-demo-mode-zero-credentials) requires **none** of the above Google API credentials.

---

### Installation

**1. Clone and navigate to the project:**

```bash
git clone <repository-url>
cd nimblevault/backend
```

**2. Create and activate a virtual environment:**

```bash
python -m venv venv
```

- **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Linux / macOS:**
  ```bash
  source venv/bin/activate
  ```

**3. Install dependencies:**

```bash
pip install -r requirements.txt
```

**4. Create the environment file:**

- **Windows (PowerShell):**
  ```powershell
  Copy-Item .env.example .env
  ```
- **Linux / macOS:**
  ```bash
  cp .env.example .env
  ```

---

### Configuration

All runtime configuration is loaded from the `.env` file via [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). The `Settings` class in [`config.py`](backend/app/core/config.py) provides type-safe defaults, validation, and LRU-cached singleton access.

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLite connection string | `sqlite+aiosqlite:///nimblevault.db` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Path to Google Drive Service Account key file | `service_account.json` |
| `GOOGLE_DRIVE_FOLDER_ID` | Default Drive folder ID to scan (optional, overridable via `--folder-id`) | *(empty)* |
| `YOUTUBE_CLIENT_SECRETS_JSON` | Path to YouTube OAuth2 client credentials | `client_secrets.json` |
| `YOUTUBE_TOKEN_JSON` | Path to persisted YouTube OAuth2 token | `youtube_token.json` |
| `YOUTUBE_PRIVACY_STATUS` | Default privacy for uploaded videos (`private` / `unlisted` / `public`) | `private` |
| `YOUTUBE_VIDEO_CATEGORY_ID` | Fallback YouTube category ID ([22 = People & Blogs](https://developers.google.com/youtube/v3/docs/videoCategories/list)) | `22` |
| `GEMINI_API_KEY` | Gemini API authentication key | *(empty — triggers fallback engine)* |
| `GEMINI_MODEL` | Gemini model for metadata generation | `gemini-3.5-flash-lite` |
| `TEMP_DOWNLOAD_DIR` | Local directory for temporary video downloads | System temp dir |
| `APP_NAME` | Application name | `NimbleVault` |
| `DEBUG` | Enable SQLAlchemy debug logging | `false` |

---

## Google API Setup

Live execution requires three Google API integrations. Each is independently configured.

### 1. Gemini API

1. Navigate to [Google AI Studio](https://aistudio.google.com/).
2. Sign in and create an API key.
3. Add the key to `backend/.env`:
   ```env
   GEMINI_API_KEY=YOUR_REAL_API_KEY
   ```

> **Note:** If the Gemini API key is missing or invalid, the pipeline automatically uses the deterministic fallback metadata engine. No manual intervention is required.

### 2. Google Drive API

NimbleVault uses a **Google Service Account** for non-interactive Drive access.

**Step-by-step:**

1. **Create or select a Google Cloud project** at [console.cloud.google.com](https://console.cloud.google.com/).

2. **Enable the Google Drive API:**
   ```
   APIs & Services → Library → Google Drive API → Enable
   ```

3. **Create a Service Account:**
   ```
   APIs & Services → Credentials → Create Credentials → Service Account
   ```
   Use any descriptive name (e.g., `drive-robot`).

4. **Generate a JSON key file:**
   ```
   Select the Service Account → Keys → Add Key → Create New Key → JSON
   ```
   Download, rename to `service_account.json`, and place at:
   ```
   backend/service_account.json
   ```

5. **Share the target Drive folder:**
   - Open `service_account.json` and copy the `client_email` value.
   - In Google Drive, right-click the target folder → **Share** → add the email as **Viewer**.

### 3. YouTube Data API v3

**Step-by-step:**

1. **Enable the API** in Google Cloud Console:
   ```
   APIs & Services → Library → YouTube Data API v3 → Enable
   ```

2. **Configure the OAuth consent screen:**
   - Set an application name (e.g., `NimbleVault`).
   - For external testing, add the authorizing Google account as a **test user**.

3. **Create an OAuth 2.0 Client ID:**
   ```
   APIs & Services → Credentials → Create Credentials → OAuth Client ID → Desktop app
   ```

4. **Download and place the credentials:**
   - Rename the downloaded file to `client_secrets.json`.
   - Place it at `backend/client_secrets.json`.

> **Note:** Google Cloud Console's UI may change over time. Follow the labels currently displayed in the console.

---

## YouTube Authentication

After placing `client_secrets.json`, run the interactive authentication helper:

```bash
cd backend
python scripts/auth_youtube.py
```

A browser window will open. Select the Google account associated with the target YouTube channel and complete the OAuth consent flow.

On success, the script persists the token to `youtube_token.json` for subsequent runs (automatic token refresh is built in).

**Verify authentication status:**

```bash
python scripts/auth_youtube.py --check
```

---

## Running the Application

All pipeline commands are run from the `backend/` directory with the virtual environment activated.

### 1. Demo Mode (Zero Credentials)

Runs a complete end-to-end simulation of all four benchmark scenarios without requiring any Google API credentials, cloud accounts, or network access.

```bash
python scripts/run_pipeline.py --demo
```

Or use the standalone demo script:

```bash
python scripts/demo.py
```

**What it demonstrates:**
- Mass content acquisition (recursive Drive traversal simulation)
- Intelligent metadata generation (deterministic fallback engine)
- Seamless distribution (simulated YouTube resumable upload)
- Idempotency & state tracking (state machine lifecycle)

> **🎯 Reviewers:** This is the fastest way to evaluate the pipeline's behavior. No setup required beyond installing dependencies.

### 2. Status Check

Inspect system readiness (database, Drive credentials, YouTube auth, Gemini config) and view all tracked video jobs:

```bash
python scripts/run_pipeline.py --status
```

### 3. Dry Run

Test the **real** Drive workflow and metadata generation while **simulating** the YouTube upload:

```bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --dry-run
```

**How to find the folder ID:** For a Drive URL like `https://drive.google.com/drive/folders/1AbCdEfGh123`, the folder ID is `1AbCdEfGh123`.

### 4. Live Pipeline ⭐

Execute the full end-to-end pipeline with real YouTube uploads:

```bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID
```

> **⚠️ Important:** Verify `YOUTUBE_PRIVACY_STATUS` in `.env` before a live run. Default is `private`.

### Additional Modes

| Mode | Command | Description |
|---|---|---|
| **Scan Only** | `--folder-id ID --scan-only` | Discover and index videos without processing or uploading |
| **Batch Process** | `--batch` | Process all pending jobs already stored in the database |
| **Synchronize** | `--sync` | Scan Drive for new content and reconcile existing YouTube records |
| **Force Reprocess** | `--folder-id ID --force` | Re-process previously completed jobs (use with caution) |

---

## Pipeline Workflow

Each video follows a deterministic, state-tracked lifecycle through the pipeline:

```
  ┌─────────────────────────────────┐
  │  1. SELECT Google Drive Folder  │
  └───────────────┬─────────────────┘
                  ▼
  ┌─────────────────────────────────┐
  │  2. RECURSIVE DISCOVERY         │  Paginated API calls, cycle detection,
  │     Walk all subfolders          │  shortcut resolution, fault isolation
  └───────────────┬─────────────────┘
                  ▼
  ┌─────────────────────────────────┐
  │  3. VIDEO IDENTIFICATION        │  MIME type + file extension matching
  │     20+ supported formats       │  across discovered files
  └───────────────┬─────────────────┘
                  ▼
  ┌─────────────────────────────────┐
  │  4. DATABASE STATE CHECK        │  Duplicate prevention via unique
  │     drive_file_id index         │  index on Google Drive file ID
  └───────────────┬─────────────────┘
                  ▼
  ┌─────────────────────────────────┐
  │  5. CHUNKED DOWNLOAD            │  8 MB chunks with exponential backoff
  │     Status: DOWNLOADING         │  retry on transient errors
  └───────────────┬─────────────────┘
                  ▼
  ┌─────────────────────────────────┐
  │  6. METADATA GENERATION         │  Gemini AI (primary) or deterministic
  │     Status: TITLING             │  fallback engine (offline)
  └───────────────┬─────────────────┘
                  ▼
  ┌─────────────────────────────────┐
  │  7. RESUMABLE UPLOAD            │  8 MB chunks, resumable protocol,
  │     Status: UPLOADING           │  exponential backoff on 429/5xx
  └───────────────┬─────────────────┘
                  ▼
  ┌─────────────────────────────────┐
  │  8. RECORD & CLEANUP            │  Store YouTube video ID, clean up
  │     Status: COMPLETED           │  temporary download files
  └─────────────────────────────────┘
```

The full Google Drive path is preserved throughout as contextual input for metadata generation (e.g., `Drive/Products/Launch_X/Tutorials/Getting_Started.mov`).

---

## Database & State Management

NimbleVault uses **SQLite** via **aiosqlite** for fully async database operations, managed through **SQLAlchemy 2.0's** async engine and session factory.

### State Machine

```
                          ┌──────────┐
                          │ PENDING  │ ◀─── New job registered
                          └────┬─────┘      (or reconciled from deleted YouTube video)
                               │
                          ┌────▼─────────┐
                          │ DOWNLOADING  │
                          └────┬─────────┘
                               │
                          ┌────▼─────┐
                          │ TITLING  │
                          └────┬─────┘
                               │
                          ┌────▼─────────┐
                          │ UPLOADING    │
                          └────┬─────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                                     ▼
     ┌────────────┐                         ┌──────────┐
     │ COMPLETED  │                         │  FAILED  │
     └────────────┘                         └──────────┘
```

### VideoJob Schema

| Column | Type | Purpose |
|---|---|---|
| `id` | `UUID (String 36)` | Primary key, auto-generated |
| `drive_file_id` | `String 255` | Google Drive file ID (**unique indexed** — prevents duplicates) |
| `file_name` | `String 512` | Original filename from Drive |
| `full_path` | `Text` | Complete virtual Drive path (used for metadata context) |
| `generated_title` | `Text` | AI-generated or fallback title |
| `youtube_video_id` | `String 255` | YouTube video ID after successful upload |
| `status` | `String 20` | Current pipeline state (`PENDING`, `DOWNLOADING`, `TITLING`, `UPLOADING`, `COMPLETED`, `FAILED`) |
| `error_log` | `Text` | Error details for failed jobs |
| `created_at` | `DateTime (tz)` | Job creation timestamp |
| `updated_at` | `DateTime (tz)` | Last modification timestamp |

**Indexes:**
- Unique index on `drive_file_id` (duplicate prevention)
- Composite index on `(status, created_at)` (query optimization)

### Why SQLite?

SQLite was chosen deliberately for this project:

1. **Zero infrastructure** — No database server to install, configure, or manage.
2. **Single-file portability** — The entire database is one `nimblevault.db` file.
3. **Async compatibility** — `aiosqlite` provides a native async interface for SQLAlchemy.
4. **Appropriate scale** — A local automation pipeline does not need PostgreSQL-level concurrency.
5. **Reviewer-friendly** — Evaluators can run the project immediately without database setup.

---

## AI Metadata Generation

### How It Works

The `GeminiService` analyzes the **full Google Drive folder path** to generate contextually relevant YouTube metadata. The folder hierarchy acts as a semantic signal — parent folders represent categories, projects, and series.

**Example transformation:**

| Drive Path | Generated Title | Category |
|---|---|---|
| `Drive/Vlogs/2024/Week12/Final_Edit.mp4` | Vlogs 2024: Week 12 Final Edit | People & Blogs (22) |
| `Drive/Products/Launch_X/Tutorials/Getting_Started.mov` | Launch X Product Tutorial: Getting Started | Education (27) |
| `Drive/Team/Archive/Q3/Marketing_Review_10-05.avi` | Team Archive Q3: Marketing Review 10-05 | People & Blogs (22) |
| `Drive/Clients/ACME/Testimonial_v2.mp4` | Client Testimonial: ACME (v2) | People & Blogs (22) |

### Dual-Engine Architecture

```
                    ┌───────────────────────┐
                    │   Full Drive Path     │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   GEMINI_API_KEY      │
                    │   configured?         │
                    └───┬───────────────┬───┘
                   Yes  │               │  No
                        ▼               ▼
              ┌─────────────┐  ┌──────────────────┐
              │  Gemini AI  │  │  Deterministic   │
              │  (Primary)  │  │  Fallback Engine │
              │             │  │                  │
              │ • Structured│  │ • Regex-based    │
              │   JSON      │  │   title rules    │
              │ • Pydantic  │  │ • Keyword-based  │
              │   schema    │  │   category map   │
              │ • temp=0.2  │  │ • Path-derived   │
              └──────┬──────┘  │   descriptions   │
                     │         └────────┬─────────┘
                     │                  │
                     └──────┬───────────┘
                            ▼
                 ┌──────────────────────┐
                 │   VideoMetadata      │
                 │   (Pydantic model)   │
                 │                      │
                 │  • title (< 100ch)   │
                 │  • description       │
                 │  • category_id       │
                 │  • tags (computed)   │
                 └──────────────────────┘
```

**Key design choice:** The deterministic fallback engine mirrors the same transformation rules as the Gemini prompt, ensuring consistent output quality regardless of which engine is active. This prevents the pipeline from stalling when the AI service is unavailable.

---

## Reliability & Error Handling

| Mechanism | Implementation | Purpose |
|---|---|---|
| **Resumable Uploads** | YouTube's resumable upload protocol | Large files can resume from the last successful chunk after interruption |
| **Chunked I/O** | 8 MB chunks for both downloads and uploads | Keeps memory usage constant regardless of video file size |
| **Exponential Backoff** | `2^n` second delays, up to 5 retries | Handles transient 429 rate-limits and 5xx server errors gracefully |
| **Fault-Isolated Traversal** | `try/except` per subfolder | A single inaccessible subfolder doesn't abort the entire scan |
| **Temp File Cleanup** | `finally` blocks + `unlink(missing_ok=True)` | Downloaded files are always cleaned up, even after errors |
| **Graceful Token Refresh** | Automatic `creds.refresh(Request())` | Expired YouTube tokens are refreshed transparently before upload |
| **Self-Healing Reconciliation** | YouTube liveness check + status reset | Deleted YouTube videos are detected and automatically re-queued for upload |
| **Quota Detection** | Parse `403 quotaExceeded` responses | Provides specific, actionable error messages for YouTube quota limits |
| **Schema Validation** | Pydantic `model_validate_json()` | Malformed Gemini responses are caught and trigger fallback metadata |

---

## Design Decisions & Rationale

### 1. Backend CLI vs. Web UI

**Decision:** Build a CLI automation engine, not a web application.

**Rationale:**
- The core problem is batch video processing — a background workflow, not an interactive user interface.
- A CLI is trivially scriptable, composable with `cron`/Task Scheduler, and requires zero frontend infrastructure.
- Local-first execution simplifies deployment and avoids the overhead of a web server, session management, and frontend build tooling.

### 2. Service-Oriented Module Design

**Decision:** Isolate each external integration into a dedicated service class.

```
drive_service.py    → Google Drive API (acquisition)
gemini_service.py   → Gemini AI API (intelligence)
youtube_service.py  → YouTube Data API (distribution)
```

**Rationale:**
- **Single Responsibility:** Each service encapsulates one external dependency, making it independently testable and replaceable.
- **Failure Isolation:** A Gemini API outage doesn't prevent Drive scanning or YouTube uploads.
- **Mockability:** Services can be stubbed for testing without touching real APIs.

### 3. Async Architecture with Thread Pool Delegation

**Decision:** Use `async/await` for the pipeline orchestrator, but delegate synchronous Google API client calls to `asyncio.to_thread()`.

**Rationale:**
- The Google API Python client library (`googleapiclient`) is synchronous and blocking.
- Wrapping blocking calls in `asyncio.to_thread()` prevents them from stalling the event loop.
- The database layer uses `aiosqlite` for natively async I/O, which integrates cleanly.
- This hybrid approach avoids rewriting the Google client while preserving async pipeline control flow.

### 4. Pydantic-Enforced Configuration & Schemas

**Decision:** Use `pydantic-settings` for configuration and `pydantic.BaseModel` for API response schemas.

**Rationale:**
- Settings are validated at startup — missing or malformed values fail fast with clear error messages.
- The `VideoMetadata` schema enforces title length (< 100 chars), valid category IDs, and description format at the data layer.
- `response_schema` in the Gemini API call forces structured JSON output, reducing post-processing.

### 5. Deterministic AI Fallback

**Decision:** Implement a complete offline metadata generation engine alongside Gemini.

**Rationale:**
- External AI services are inherently unreliable (rate limits, outages, billing issues).
- The fallback engine uses regex-based title transformation and keyword-based category inference.
- This ensures the pipeline produces useful output even with zero API keys configured.
- The demo mode relies entirely on this fallback, enabling zero-credential evaluation.

### 6. SQLite with Async ORM

**Decision:** Use SQLite via `aiosqlite` + `SQLAlchemy 2.0` async instead of a client-server database.

**Rationale:**
- A local automation tool doesn't benefit from PostgreSQL's concurrency model.
- SQLite's single-file database is trivially portable and requires zero setup.
- `aiosqlite` provides native async support, eliminating the need for thread-pool-based DB access.
- Unique constraints and composite indexes provide adequate data integrity for this use case.

### 7. Self-Healing YouTube Reconciliation

**Decision:** Automatically detect deleted YouTube videos and re-queue them for upload.

**Rationale:**
- YouTube videos can be removed externally (content moderation, manual deletion, policy violations).
- Without reconciliation, the database would permanently consider these jobs "completed" — a stale state.
- The liveness check uses HTTP scraping (not API quota) to minimize impact on the YouTube API quota budget.

---

## Performance Considerations

### Drive Traversal Complexity

The recursive folder traversal visits each folder and file exactly once, guarded by a `visited_folder_ids` set:

```
Time complexity:  O(N)   where N = total folders + files discovered
Space complexity: O(N)   for the visited set + results list
```

Subfolder errors are caught and logged individually, so a single inaccessible folder doesn't interrupt traversal of the remaining tree.

### Memory Efficiency

Videos are processed using **chunked streaming** (8 MB segments) for both downloads and uploads. This means:

- Memory usage is approximately **constant** regardless of video file size.
- A 5 GB video uses the same working memory as a 50 MB video during transfer.
- Temporary files are written to disk and cleaned up after processing.

### Database Queries

The composite index on `(status, created_at)` optimizes the most common access pattern: fetching pending jobs ordered by creation time.

---

## Security Considerations

### Sensitive Files

The following files contain credentials or tokens and are excluded via [`.gitignore`](.gitignore):

| File | Contains | Source |
|---|---|---|
| `.env` | API keys, database URL, configuration | Created from `.env.example` |
| `service_account.json` | Google Cloud Service Account private key | Downloaded from GCP Console |
| `client_secrets.json` | YouTube OAuth2 client ID and secret | Downloaded from GCP Console |
| `youtube_token.json` | Persisted YouTube OAuth2 access/refresh token | Generated by `auth_youtube.py` |

### Best Practices

- **Never** hard-code API keys in source code.
- **Never** commit credential files to version control.
- Verify `.gitignore` coverage before pushing to a remote repository.
- Use `private` as the default `YOUTUBE_PRIVACY_STATUS` to avoid accidental public uploads.

### Credential Rotation

If a credential is accidentally exposed:

1. **Revoke** the compromised key/token in the [Google Cloud Console](https://console.cloud.google.com/).
2. **Generate** a new credential and replace the local file.
3. **Audit** git history — use `git filter-branch` or [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) to remove secrets from commit history.

---

## Troubleshooting

### Google Drive: `403 Access Denied`

**Cause:** The Service Account does not have access to the target Drive folder.

**Fix:**
1. Open `service_account.json` and copy the `client_email` value.
2. In Google Drive, right-click the target folder → **Share**.
3. Add the Service Account email with **Viewer** access.
4. Re-run the pipeline.

---

### YouTube: `403 quotaExceeded`

**Cause:** The Google Cloud project has exhausted its daily YouTube API quota (default: 10,000 units/day; each upload costs 1,600 units).

**Fix:**
- Use `--dry-run` mode for testing to avoid consuming upload quota.
- Check quota usage in the [Google Cloud Console API Dashboard](https://console.cloud.google.com/apis/dashboard).
- Wait for quota reset at midnight Pacific Time.

---

### YouTube Authentication Failure

**Checklist:**
- [ ] `client_secrets.json` exists in `backend/`.
- [ ] YouTube Data API v3 is **enabled** in the Google Cloud project.
- [ ] OAuth consent screen is configured with the correct test users.
- [ ] The command is run from the `backend/` directory.

**Re-authenticate:**
```bash
python scripts/auth_youtube.py
```

---

### Gemini Metadata Generation Failure

**Checklist:**
- [ ] `GEMINI_API_KEY` is set in `.env` with a valid key.
- [ ] The configured `GEMINI_MODEL` is available for the API account.

**Note:** If Gemini fails, the pipeline automatically falls back to the deterministic engine — no manual intervention needed.

---

### Python Dependency Errors

```bash
# Ensure the virtual environment is active, then:
pip install -r requirements.txt

# Verify Python version (requires 3.10+):
python --version
```

---

## Quick Reference: CLI Commands

| Purpose | Command |
|---|---|
| **Run demo** (zero credentials) | `python scripts/demo.py` |
| **Run demo** via CLI | `python scripts/run_pipeline.py --demo` |
| **Check system readiness** | `python scripts/run_pipeline.py --status` |
| **Authenticate YouTube** | `python scripts/auth_youtube.py` |
| **Verify YouTube auth** | `python scripts/auth_youtube.py --check` |
| **Scan only** (no processing) | `python scripts/run_pipeline.py --folder-id ID --scan-only` |
| **Dry run** (simulated upload) | `python scripts/run_pipeline.py --folder-id ID --dry-run` |
| **Live pipeline** | `python scripts/run_pipeline.py --folder-id ID` |
| **Process pending jobs** | `python scripts/run_pipeline.py --batch` |
| **Sync Drive + YouTube** | `python scripts/run_pipeline.py --sync` |
| **Force reprocessing** | `python scripts/run_pipeline.py --folder-id ID --force` |

> All commands are run from the `backend/` directory with the virtual environment activated.

---

## 🚀 Reviewer Quick Start

**For reviewers who want to evaluate the project with zero cloud setup:**

```bash
# 1. Navigate to the backend
cd backend

# 2. Create and activate virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the zero-credential demo
python scripts/run_pipeline.py --demo
# or
python scripts/demo.py
```

The demo executes all four benchmark scenarios (Weekly Vlog, Product Tutorial, Internal Meeting Archive, Client Testimonial) and validates:

- ✅ **Mass Content Acquisition** — Recursive Drive traversal with chunked streaming
- ✅ **Intelligent Metadata Generation** — Context-aware titling from folder hierarchy
- ✅ **Seamless Distribution** — Resumable YouTube upload simulation
- ✅ **Idempotency & State Tracking** — Full state machine lifecycle audit

**No Google Cloud project, API keys, or network access required.**

---

<p align="center">
  <sub>Built with Python · Powered by Google Gemini AI · NimbleVault</sub>
</p>
