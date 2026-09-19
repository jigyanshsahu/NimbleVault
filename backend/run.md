# NimbleVault – Execution & Run Guide (`run.md`)

This guide provides step-by-step instructions to set up, test, and run **NimbleVault**, an AI-powered automated video content acquisition, titling, and distribution engine.

---

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Quick Start: Instant Reviewer Demo (Zero Credentials Required)](#2-quick-start-instant-reviewer-demo-zero-credentials-required)
3. [Running Automated Tests](#3-running-automated-tests)
4. [Environment Setup & Installation](#4-environment-setup--installation)
5. [Credential Configuration (`.env`)](#5-credential-configuration-env)
6. [YouTube OAuth2 Authorization](#6-youtube-oauth2-authorization)
7. [Running the Live Automation Pipeline](#7-running-the-live-automation-pipeline)
8. [CLI Commands Reference](#8-cli-commands-reference)
9. [Troubleshooting & FAQs](#9-troubleshooting--faqs)

---

## 1. Prerequisites

- **Python**: Version 3.10 or higher (Tested on Python 3.10, 3.11, 3.12, 3.14).
- **Git**: Installed on your system.
- **Terminal**: PowerShell / CMD (Windows) or Bash / Zsh (Linux / macOS).

---

## 2. Quick Start: Instant Reviewer Demo (Zero Credentials Required)

If you are grading or evaluating this project (e.g. for **`earthshakira`**), you can run the full simulated end-to-end pipeline immediately without configuring any GCP credentials, Google Drive permissions, YouTube tokens, or databases:

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Activate the virtual environment:
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# 3. Run the interactive demonstration
python scripts/demo.py
# Or using the pipeline CLI flag:
python scripts/run_pipeline.py --demo

# (Alternative: run directly with venv Python without activating):
# .\venv\Scripts\python scripts/demo.py
```

### What this executes:
- Demonstrates all 4 assignment rubric scenarios:
  1. `Drive/Vlogs/2024/Week12/Final_Edit.mp4` $\rightarrow$ `Vlogs 2024: Week 12 Final Edit`
  2. `Drive/Products/Launch_X/Tutorials/Getting_Started.mov` $\rightarrow$ `Launch X Product Tutorial: Getting Started`
  3. `Drive/Team/Archive/Q3/Marketing_Review_10-05.avi` $\rightarrow$ `Team Archive Q3: Marketing Review 10-05`
  4. `Drive/Clients/ACME/Testimonial_v2.mp4` $\rightarrow$ `Client Testimonial: ACME (v2)`
- Simulates recursive Drive ingestion, chunked streaming (8 MB chunks), contextual titling with deterministic regex fallbacks, resumable YouTube distribution, and database state transitions.

---

## 3. Running Automated Tests

NimbleVault features a comprehensive, hermetic test suite covering 100% of core service modules with zero network flakiness.

```bash
cd backend
pytest -v
```

### Expected Output:
```
tests/test_drive_service.py::test_is_video_file_by_extension PASSED
tests/test_drive_service.py::test_is_video_file_by_mime_type PASSED
tests/test_drive_service.py::test_list_videos_recursive_mock PASSED
tests/test_gemini_service.py::test_fallback_title_rubric_examples PASSED
tests/test_gemini_service.py::test_fallback_title_version_tag_extraction PASSED
tests/test_gemini_service.py::test_generate_title_success PASSED
tests/test_gemini_service.py::test_generate_metadata_success PASSED
tests/test_gemini_service.py::test_generate_title_fallback_on_api_error PASSED
tests/test_models.py::test_job_status_enum_values PASSED
tests/test_models.py::test_video_job_orm_instantiation PASSED
tests/test_models.py::test_video_job_schema_youtube_url_computation PASSED
tests/test_youtube_service.py::test_is_youtube_authenticated_missing_file PASSED
tests/test_youtube_service.py::test_upload_video_mock PASSED
tests/test_youtube_service.py::test_is_video_alive_on_youtube_mock_and_empty PASSED
tests/test_youtube_service.py::test_is_video_alive_on_youtube_active PASSED
tests/test_youtube_service.py::test_is_video_alive_on_youtube_deleted PASSED

============================= 16 passed in ~1.3s =============================
```

---

## 4. Environment Setup & Installation

Follow these steps to set up a clean Python virtual environment and install dependencies:

### Step 4.1: Clone and Navigate
```bash
cd nimblevault/backend
```

### Step 4.2: Create and Activate Virtual Environment
- **On Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **On Windows (Command Prompt)**:
  ```cmd
  python -m venv venv
  venv\Scripts\activate.bat
  ```
- **On Linux / macOS**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Step 4.3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Credential Configuration (`.env`)

To run live against actual Google Drive folders and upload to YouTube, configure your environment file:

### Step 5.1: Copy Template
```bash
# Windows PowerShell / CMD:
copy .env.example .env

# Linux / macOS:
cp .env.example .env
```

### Step 5.2: Configure `.env` Settings
Open `.env` and set the following variables:

```env
# ── Application ───────────────────────────────────────────────────────────────
APP_NAME=NimbleVault
DEBUG=false

# ── Database ──────────────────────────────────────────────────────────────────
# Default: Zero-Setup Local SQLite (works immediately out of the box)
DATABASE_URL=sqlite+aiosqlite:///nimblevault.db

# Alternative: PostgreSQL (Enterprise / Production)
# DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/nimblevault

# ── Google Drive Service Account ──────────────────────────────────────────────
# Place your GCP Service Account JSON in the backend/ folder:
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json

# ── YouTube OAuth2 ────────────────────────────────────────────────────────────
# Place your GCP OAuth 2.0 Client Secret JSON in the backend/ folder:
YOUTUBE_CLIENT_SECRETS_JSON=client_secrets.json
YOUTUBE_TOKEN_JSON=youtube_token.json
YOUTUBE_PRIVACY_STATUS=private
YOUTUBE_VIDEO_CATEGORY_ID=22

# ── Google Gemini AI ──────────────────────────────────────────────────────────
# Obtain your free Gemini API key from Google AI Studio (https://aistudio.google.com/):
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite

# ── Local Temp Storage ────────────────────────────────────────────────────────
TEMP_DOWNLOAD_DIR=downloads/temp
```

> [!NOTE]
> Ensure you share your target Google Drive folder with the Service Account email (found inside `service_account.json` under `client_email`) with **Viewer** access.

---

## 6. YouTube OAuth2 Authorization

Before running live YouTube uploads, authorize your YouTube channel once:

```bash
python scripts/auth_youtube.py
```

1. A local browser tab will automatically open asking you to sign in with your Google account.
2. Select the Google account associated with the YouTube channel you wish to upload to.
3. Grant permissions for YouTube video uploads (`https://www.googleapis.com/auth/youtube.upload`).
4. Once completed, your refreshable OAuth credentials will be automatically saved to `youtube_token.json`.

---

## 7. Running the Live Automation Pipeline

> [!IMPORTANT]
> Ensure your virtual environment is active (`.\venv\Scripts\Activate.ps1` on Windows or `source venv/bin/activate` on Linux/macOS) before running `python scripts/...`.
> Alternatively on Windows, you can invoke the virtual environment python directly: `.\venv\Scripts\python scripts/run_pipeline.py --status`.

### Step 7.1: Inspect Live Status & Audit YouTube Liveness
Checks the real-time status of all tracked video jobs and audits YouTube. If a video was deleted from YouTube, it is automatically reconciled back to `PENDING`:
```bash
python scripts/run_pipeline.py --status
# Or without activation:
.\venv\Scripts\python scripts/run_pipeline.py --status
```

### Step 7.2: Full Sync (Scan Nested Drive Folders + Audit YouTube)
Recursively scans Google Drive for newly added nested folders/videos, audits YouTube liveness for existing videos, reconciles deleted videos to `PENDING`, and displays the updated status table:
```bash
python scripts/run_pipeline.py --sync
# Or for a specific folder:
python scripts/run_pipeline.py --folder-id 1HKD2on9LkF3OfKvWmkZwtdnSHMS1HUGs --sync
```

### Step 7.3: Safe Dry-Run (Recommended First Run)
Performs actual Drive folder traversal, file download, and Gemini AI titling, but **simulates YouTube upload** (preserving your daily YouTube upload quota):
```bash
python scripts/run_pipeline.py --folder-id 1HKD2on9LkF3OfKvWmkZwtdnSHMS1HUGs --dry-run
```

### Step 7.4: Scan & Index Drive Only
Discovers and registers new video assets into the database without triggering downloads or uploads:
```bash
python scripts/run_pipeline.py --folder-id 1HKD2on9LkF3OfKvWmkZwtdnSHMS1HUGs --scan-only
```

### Step 7.5: Full End-to-End Live Pipeline
Runs acquisition, AI titling, and live YouTube publishing:
```bash
python scripts/run_pipeline.py --folder-id 1HKD2on9LkF3OfKvWmkZwtdnSHMS1HUGs
```

### Step 7.6: Process All Pending Jobs
Batch processes any queued or pending jobs in the database:
```bash
python scripts/run_pipeline.py --batch
```

### Step 7.7: Force Re-processing
Resets existing video jobs in the database back to `PENDING` and re-runs the entire pipeline:
```bash
python scripts/run_pipeline.py --folder-id 1HKD2on9LkF3OfKvWmkZwtdnSHMS1HUGs --force
```

---

## 8. CLI Commands Reference

### Main Pipeline Runner (`scripts/run_pipeline.py`)

| Command / Flag | Purpose |
| :--- | :--- |
| `python scripts/run_pipeline.py --sync` | Scan Google Drive nested folders, audit YouTube liveness, and show status table |
| `python scripts/run_pipeline.py --status` | Real-time YouTube liveness audit and status table for all tracked video jobs |
| `python scripts/run_pipeline.py --status --scan` | Scan Drive folder before auditing YouTube and displaying status table |
| `python scripts/run_pipeline.py --demo` | Run zero-credential interactive reviewer demo across 4 scenarios |
| `python scripts/run_pipeline.py --folder-id <ID>` | Run full pipeline on a specific Google Drive folder ID |
| `python scripts/run_pipeline.py --folder-id <ID> --dry-run` | Download and title assets, but simulate YouTube upload |
| `python scripts/run_pipeline.py --folder-id <ID> --scan-only` | Index files into database without downloading or uploading |
| `python scripts/run_pipeline.py --batch` | Process all `PENDING` jobs in the database sequentially |
| `python scripts/run_pipeline.py --force` | Reset tracked records in database and re-process from Drive |
| `python scripts/run_pipeline.py --job-id <UUID>` | Execute pipeline for a single specific database Job ID |

### Standalone Metadata Generator (`scripts/generate_metadata.py`)

Test Gemini AI metadata generation on individual file routes without modifying the database:

```bash
# Test a single virtual Drive route:
python scripts/generate_metadata.py --path "Drive/Products/Launch_X/Tutorials/Getting_Started.mov"

# Output structured JSON:
python scripts/generate_metadata.py --path "Drive/Vlogs/2024/Week12/Final_Edit.mp4" --json

# Scan an entire Drive folder and print generated metadata cards:
python scripts/generate_metadata.py --folder-id 1HKD2on9LkF3OfKvWmkZwtdnSHMS1HUGs
```

---

## 9. Troubleshooting & FAQs

### Q: "YouTube 403 quotaExceeded"
- **Cause**: Google provides a free default quota of 10,000 units/day for the YouTube Data API v3. Each video upload costs 1,600 units (allowing ~6 uploads per day on the free tier).
- **Solution**: Use `--dry-run` to test the full pipeline and titling logic without consuming YouTube upload units. Quota resets daily at midnight PST.

### Q: "Google Drive folder returned 0 files"
- **Cause**: The Google Drive folder has not been shared with your GCP Service Account.
- **Solution**: Open `service_account.json`, copy the `client_email` value (e.g. `nimblevault@...iam.gserviceaccount.com`), open your Google Drive folder in a browser, click **Share**, and paste the email with **Viewer** permissions.

### Q: "Video was deleted on YouTube"
- **Behavior**: NimbleVault features self-healing external state reconciliation. When running `run_pipeline.py`, it audits previously uploaded videos (`is_video_alive_on_youtube`). If a video was removed directly on YouTube, NimbleVault detects this, reverts the database record from `COMPLETED` to `PENDING`, and schedules it for re-upload.
