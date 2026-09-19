# NimbleVault – AI-Powered Content Handler

> [!TIP]
> ### Quick Reviewer Evaluation Kit for `earthshakira`
> This project is fully configured for instantaneous local grading without requiring cloud credentials or database setup:
> 1. **Zero-Credential Interactive Demonstration (All 4 Rubric Scenarios)**:
>    ```bash
>    cd backend
>    python scripts/demo.py
>    ```
> 2. **Hermetic Automated Test Suite (21 Passing Tests, 100% Pass Rate)**:
>    ```bash
>    cd backend
>    pytest -v
>    ```
> 3. **Sharing**: This private repository is shared with GitHub user **`earthshakira`** per submission guidelines.

---

## Architecture Overview

```
 ┌─────────────────────────────────────────────────────────────┐
 │                     Google Drive (Cloud)                    │
 │         Target Folder (with arbitrarily nested trees)       │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                 [1] Mass Content Acquisition
                     (Recursive Walk & Chunked Stream)
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                      NimbleVault Core                       │
 │                                                             │
 │  ┌─────────────────┐   ┌─────────────────┐   ┌────────────┐ │
 │  │ Database State  │   │  Gemini AI      │   │ YouTube    │ │
 │  │ (PostgreSQL/    │   │  Title Engine   │   │ Resumable  │ │
 │  │  SQLAlchemy)    │   │  (gemini-3.5)   │   │ Uploader   │ │
 │  └────────┬────────┘   └────────┬────────┘   └──────┬─────┘ │
 └───────────┼─────────────────────┼───────────────────┼───────┘
             │                     │                   │
             │             [2] Contextual Titling      │
             │                     │                   │
             │                     ▼                   │
             │           [3] Video Distribution        │
             │                     │                   │
             │                     ▼                   │
             │           [4] Self-Healing State Sync   │
             │                                         │
             ▼                                         ▼
 ┌────────────────────────┐               ┌────────────────────┐
 │  Next.js 14 Dashboard  │               │      YouTube       │
 │  (Interactive Control) │               │   (Public/Unlisted)│
 └────────────────────────┘               └────────────────────┘
```

---

## Core Features

### 1. Mass Content Acquisition (Google Drive API v3)
- **Recursive Folder Traversal**: Recursively scans any Google Drive folder structure, including multi-level subdirectories, identifying supported video mime types (`video/mp4`, `video/quicktime`, `video/x-msvideo`, etc.).
- **Virtual Path Preservation**: Constructs the semantic Drive virtual path (e.g. `Drive/Products/Launch_X/Tutorials/Getting_Started.mov`), which serves as the contextual input for AI titling.
- **Chunked Stream Downloads**: Streams large files to local temporary storage using 8 MB chunks via `MediaIoBaseDownload`, preventing high memory consumption.
- **Immediate Disk Cleanup**: Automatically unlinks temporary files immediately following successful or failed upload attempts to maintain zero lingering storage overhead.

### 2. Intelligent Metadata Generation (Google Gemini AI)
- **Context-Aware Title Generation**: Uses `gemini-3.5-flash-lite` to extract hierarchy, categories, dates, and version tags from raw file paths and transform them into engaging, discoverable titles.
- **Benchmark-Aligned Formatting**:
  - `Drive/Vlogs/2024/Week12/Final_Edit.mp4` $\rightarrow$ `Vlogs 2024: Week 12 Final Edit`
  - `Drive/Products/Launch_X/Tutorials/Getting_Started.mov` $\rightarrow$ `Launch X Product Tutorial: Getting Started`
  - `Drive/Team/Archive/Q3/Marketing_Review_10-05.avi` $\rightarrow$ `Team Archive Q3: Marketing Review 10-05`
  - `Drive/Clients/ACME/Testimonial_v2.mp4` $\rightarrow$ `Client Testimonial: ACME (v2)`
- **Deterministic Fallback Engine**: If the Gemini API encounters rate limits (429) or network outages, a built-in regex fallback instantly formats the title without blocking or failing the pipeline.

### 3. Seamless Distribution (YouTube Data API v3)
- **Resumable Uploads**: Uploads video files in 8 MB chunks with resumable sessions, handling transient connection drops gracefully.
- **OAuth2 Token Auto-Refresh**: Manages refreshable OAuth2 credentials persisted in `youtube_token.json`.
- **Configurable Privacy & Tags**: Sets titles, auto-generated descriptions, category IDs, and privacy states (`private`, `unlisted`, or `public`).

### 4. External State Reconciliation & Self-Healing (YouTube Liveness)
- **Desync Prevention**: If an uploaded video is subsequently deleted or removed directly on YouTube, NimbleVault automatically detects the missing video via playability verification without requiring excess OAuth scopes.
- **Automated State Rollback**: Reverts database status from `COMPLETED` back to `PENDING` during folder scans, pipeline runs, or on-demand via `POST /api/sync`.
- **Dashboard Audit Button**: Includes an interactive **"Sync YouTube"** button in the Next.js frontend to audit and reconcile remote state with real-time toast feedback.

---

## Design Decisions & Architectural Justifications

### 1. Database Justification (Why a Database is Essential)
A relational database (PostgreSQL via SQLAlchemy + `asyncpg`) is used for the following reasons:
- **Duplicate Prevention (Idempotency)**: Videos stored in Drive have unique IDs (`drive_file_id`). By enforcing a `UNIQUE` constraint and index on `drive_file_id`, NimbleVault guarantees that repeated scans will never re-upload or duplicate content.
- **Granular Pipeline Lifecycle**: Long-running video uploads can take minutes or fail halfway. The database maintains the exact state machine:
  $$\text{PENDING} \longrightarrow \text{DOWNLOADING} \longrightarrow \text{TITLING} \longrightarrow \text{UPLOADING} \longrightarrow \text{COMPLETED / FAILED}$$
- **Audit & Error Logging**: When an API quota or network error occurs, the exact traceback is stored in `error_log`, allowing targeted retries without re-scanning the entire folder.
- **Pre-Upload Review / Human-in-the-Loop**: Users can view pending items in the dashboard, review or edit the AI-generated title inline before triggering upload.

### 2. Dual Execution Modalities (CLI + Web UI)
- **Headless CLI (`scripts/run_pipeline.py`)**: Ideal for cron jobs, server scheduled tasks, or CI/CD pipelines. Supports `--folder-id`, `--dry-run`, and `--batch` flags.
- **FastAPI + Next.js UI**: Provides an interactive dashboard for operators to scan folders, monitor real-time progress badges, modify titles, and launch batch processing.

---

## Project Structure

```
nimblevault/
├── README.md                           # Comprehensive documentation & design justification
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py               # REST API endpoints (/api/scan, /api/jobs, etc.)
│   │   ├── core/
│   │   │   ├── config.py               # Pydantic Settings & environment loader
│   │   │   └── database.py             # Async SQLAlchemy engine & session factory
│   │   ├── models/
│   │   │   └── video.py                # VideoJob ORM model & Pydantic schemas
│   │   ├── services/
│   │   │   ├── drive_service.py        # Recursive Google Drive scanner & downloader
│   │   │   ├── gemini_service.py       # Gemini AI title generation with fallback
│   │   │   └── youtube_service.py      # YouTube OAuth2 & resumable uploader
│   │   └── main.py                     # FastAPI application factory & lifespan
│   ├── scripts/
│   │   ├── run_pipeline.py             # Standalone CLI pipeline runner
│   │   └── auth_youtube.py             # One-click YouTube OAuth browser authorization
│   ├── service_account.json            # Google Service Account credentials (Drive)
│   ├── client_secrets.json             # Google OAuth2 Client Secrets (YouTube)
│   ├── requirements.txt                # Python dependencies
│   └── .env                            # Backend configuration & API keys
└── frontend/
    ├── app/                            # Next.js 14 App Router
    ├── components/                     # FolderScanner, JobTable, StatusBadge
    └── package.json                    # Frontend dependencies
```

---

## Setup & Installation

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** & npm
- A **Google Cloud Platform (GCP)** project with:
  - Google Drive API enabled (Service Account JSON saved as `backend/service_account.json`)
  - YouTube Data API v3 enabled (OAuth 2.0 Client ID saved as `backend/client_secrets.json`)
  - Gemini API key (from Google AI Studio)

### 2. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create or edit `backend/.env`:
```env
APP_NAME=NimbleVault
DEBUG=false

# Database URL (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/<dbname>?ssl=require

# Google Drive Service Account
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json

# YouTube OAuth
YOUTUBE_CLIENT_SECRETS_JSON=client_secrets.json
YOUTUBE_TOKEN_JSON=youtube_token.json
YOUTUBE_PRIVACY_STATUS=private
YOUTUBE_VIDEO_CATEGORY_ID=22

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite

# Temporary Download Directory
TEMP_DOWNLOAD_DIR=downloads/temp

# CORS
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

---

## Execution Guide

### Option A: Standalone CLI Runner (Recommended for Direct Testing)

1. **One-Time YouTube Authorization** (Opens browser for consent):
   ```bash
   python scripts/auth_youtube.py
   ```
   *Note: If you run without YouTube authorization, the pipeline automatically runs in simulated dry-run mode for the upload step.*

2. **Run Full Pipeline** on a Google Drive folder:
   ```bash
   python scripts/run_pipeline.py --folder-id 1HKD2on9LkF3OfKvWmkZwtdnSHMS1HUGs
   ```

3. **Dry-Run Mode** (Scans Drive, downloads file, generates AI title, records to DB, simulates upload):
   ```bash
   python scripts/run_pipeline.py --folder-id 1HKD2on9LkF3OfKvWmkZwtdnSHMS1HUGs --dry-run
   ```

4. **Scan-Only Mode** (Indexes new videos into DB without downloading or uploading):
   ```bash
   python scripts/run_pipeline.py --folder-id 1HKD2on9LkF3OfKvWmkZwtdnSHMS1HUGs --scan-only
   ```

5. **Batch Process Pending Jobs**:
   ```bash
   python scripts/run_pipeline.py --batch
   ```

---

### Option B: FastAPI Backend & Next.js Web UI

1. **Start Backend Server**:
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```
   - API Docs: `http://localhost:8000/docs`
   - Health Check: `http://localhost:8000/health`

2. **Start Frontend Dashboard**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   - Dashboard: `http://localhost:3000`

---

## REST API Specification

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/scan` | Recursively scans a Drive folder and indexes new video jobs |
| `POST` | `/api/sync` | Audits completed records against YouTube and reconciles deleted videos |
| `GET` | `/api/jobs` | Retrieves all video jobs ordered by creation timestamp |
| `PATCH` | `/api/jobs/{id}/title` | Inline manual title override for a pending job |
| `POST` | `/api/process/{id}` | Enqueues processing pipeline for a single job |
| `POST` | `/api/process-batch` | Sequentially processes all pending jobs in the queue |
| `GET` | `/health` | Service health status check |

---

## Verification & Test Results

The pipeline has been verified with live test executions:
- **Test Folder**: `1HKD2on9LkF3OfKvWmkZwtdnSHMS1HUGs`
- **Discovered Asset**: `Drive/earth2/file_example_MOV_1920_2_2MB.mov` (2.14 MB)
- **AI Generated Title**: `"Earth2: File Example MOV 1920 2 2MB"`
- **Pipeline Progression**: `DOWNLOADING (100%)` $\rightarrow$ `TITLING` $\rightarrow$ `UPLOADING` $\rightarrow$ `COMPLETED`
- **Temp Cleanup**: Local video file automatically removed upon completion.
- **Duplicate Protection**: Verified that subsequent scans detect the indexed `drive_file_id` and skip re-processing.
- **Self-Healing Reconciliation**: Detected YouTube deletions and successfully reset desynced jobs to `PENDING`.

---

## Automated Test Suite

NimbleVault includes a comprehensive `pytest` test suite covering unit and integration testing across all layers (21 passing tests, 100% pass rate):

```bash
cd backend
pytest -v
```

### Test Coverage Areas (21 Tests):
1. **Google Drive Service (`tests/test_drive_service.py`)** [3 tests]:
   - MIME type detection and extension fallback logic.
   - Mocked recursive traversal verifying multi-level nested folders and path preservation.
2. **Gemini Titling Service (`tests/test_gemini_service.py`)** [5 tests]:
   - Transformation patterns matching all 4 assignment rubric examples.
   - Version tag parsing `(v2)` and error fallback handling.
   - Structured `VideoMetadata` model generation.
3. **YouTube Distribution Service (`tests/test_youtube_service.py`)** [5 tests]:
   - OAuth credential presence checks.
   - Upload snippet payload construction and title truncation rules.
   - Liveness verification (`is_video_alive_on_youtube`) for active, removed, and mock videos.
4. **Data Models & Validation (`tests/test_models.py`)** [4 tests]:
   - Job lifecycle enum validation.
   - Computed fields (`youtube_url`) and input schema constraints.
5. **FastAPI Endpoints (`tests/test_api.py`)** [4 tests]:
   - Health check probe (`/health`).
   - Job listing endpoint (`/api/jobs`).
   - Title update validation error handling.
   - External state sync audit (`/api/sync`).

---

## Submission & Sharing Instructions

Per assignment requirements, this repository is hosted on GitHub as a private repository.

### Adding Reviewer `earthshakira`:
1. Navigate to the repository on GitHub: `https://github.com/jigyanshsahu/NimbleVault`
2. Go to **Settings** $\rightarrow$ **Collaborators**.
3. Click **Add people**.
4. Search for **`earthshakira`** and click **Add earthshakira to this repository**.
5. An invitation will be sent granting full read/review access.


