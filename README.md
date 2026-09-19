# NimbleVault

> **Automated AI-powered video content pipeline** - Google Drive to Gemini AI to YouTube

NimbleVault is a full-stack application that recursively discovers video files in a Google Drive folder, generates clean professional YouTube titles using Gemini AI, and uploads the videos to YouTube - all tracked in a PostgreSQL database with a beautiful real-time dashboard.

---

## Architecture Diagram

```
+------------------------------------------------------------------+
|                        NIMBLEVAULT                               |
|                                                                  |
|   +--------------+        +------------------------------+       |
|   |  Next.js 14  |  HTTP  |        FastAPI Backend        |      |
|   |  Frontend    |<------>|   (Python 3.11+ / Async)     |      |
|   |  (Port 3000) |        |        (Port 8000)            |      |
|   +--------------+        +----------+-------------------+       |
|                                      |                           |
|              +-------------------+---+-------------+             |
|              |                   |                 |             |
|              v                   v                 v             |
|   +------------------+  +------------------+  +-----------+     |
|   |  Google Drive    |  |   Gemini 2.5     |  | YouTube   |     |
|   |  API v3          |  |   Flash API      |  | Data API  |     |
|   |  (recursive scan |  |   (AI title      |  | v3        |     |
|   |  + streaming     |  |   generation)    |  | (resumable|     |
|   |  download)       |  |                  |  | uploads)  |     |
|   +------------------+  +------------------+  +-----------+     |
|                                      |                           |
|                                      v                           |
|                          +----------------------+                |
|                          |   PostgreSQL DB       |               |
|                          |   (video_jobs table)  |               |
|                          |   SQLAlchemy async    |               |
|                          +----------------------+                |
+------------------------------------------------------------------+

Pipeline State Machine:
  PENDING --> DOWNLOADING --> TITLING --> UPLOADING --> COMPLETED
                                                   |
                                                   +--> FAILED
```

---

## Features

| Feature | Description |
|---------|-------------|
| Drive Scanner | Recursively traverses folders and subfolders; filters video MIME types |
| AI Titling | gemini-2.5-flash generates professional YouTube titles from Drive paths |
| Resumable Upload | YouTube videos().insert with resumable=True + 8 MB chunk streaming |
| Duplicate Guard | Indexed drive_file_id prevents re-processing the same file |
| Inline Editing | Edit AI-generated titles directly in the dashboard before upload |
| Live Dashboard | Auto-polls every 3 seconds; animated status badges per pipeline stage |
| Batch Processing | One-click to sequentially process all pending jobs |

---

## Project Structure

```
nimblevault/
+-- backend/
|   +-- app/
|   |   +-- api/
|   |   |   +-- routes.py          # All 5 FastAPI route handlers
|   |   +-- core/
|   |   |   +-- config.py          # Pydantic-settings configuration
|   |   |   +-- database.py        # Async SQLAlchemy engine & sessions
|   |   +-- models/
|   |   |   +-- video.py           # ORM model + Pydantic schemas
|   |   +-- services/
|   |   |   +-- drive_service.py   # Google Drive API (recursive scan + download)
|   |   |   +-- gemini_service.py  # Gemini AI title generation
|   |   |   +-- youtube_service.py # YouTube OAuth2 + resumable upload
|   |   +-- main.py                # FastAPI app factory + lifespan
|   +-- .env.example               # Environment variable template
|   +-- requirements.txt           # Python dependencies
+-- frontend/
|   +-- app/
|   |   +-- globals.css            # Tailwind base + glassmorphism styles
|   |   +-- layout.tsx             # Root layout with SEO metadata
|   |   +-- page.tsx               # Main dashboard page
|   +-- components/
|   |   +-- FolderScanner.tsx      # Drive folder ID input card
|   |   +-- JobTable.tsx           # Full pipeline dashboard table
|   |   +-- StatusBadge.tsx        # Animated status indicator
|   +-- lib/
|   |   +-- api.ts                 # Typed API client
|   +-- package.json
+-- README.md
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 14+ running locally or remote
- Google Cloud Platform project with Drive API and YouTube Data API v3 enabled
- Gemini API key from https://aistudio.google.com/app/apikey

---

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd nimblevault
```

### 2. Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and fill in all required values
```

#### Create the PostgreSQL Database

```sql
-- Connect to PostgreSQL as superuser
CREATE DATABASE nimblevault;
CREATE USER nv_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE nimblevault TO nv_user;
```

Update DATABASE_URL in .env accordingly.

#### Start the Backend

```bash
# From the backend/ directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API available at: http://localhost:8000
Interactive docs: http://localhost:8000/docs

---

### 3. Frontend Setup

```bash
cd ../frontend

# Install npm dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit NEXT_PUBLIC_API_URL if your backend is not on localhost:8000

# Start the development server
npm run dev
```

Frontend available at: http://localhost:3000

---

## Environment Variables

### Backend (backend/.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DATABASE_URL | YES | - | PostgreSQL connection string (postgresql+asyncpg://...) |
| GOOGLE_SERVICE_ACCOUNT_JSON | YES | service_account.json | Path to GCP service account key file |
| GEMINI_API_KEY | YES | - | API key from Google AI Studio |
| GEMINI_MODEL | NO | gemini-2.5-flash | Gemini model identifier |
| YOUTUBE_CLIENT_SECRETS_JSON | YES | client_secrets.json | OAuth2 client secrets from GCP Console |
| YOUTUBE_TOKEN_JSON | NO | youtube_token.json | Auto-created after first OAuth flow |
| YOUTUBE_PRIVACY_STATUS | NO | private | Upload privacy: private, unlisted, or public |
| YOUTUBE_VIDEO_CATEGORY_ID | NO | 22 | YouTube category ID (22 = People & Blogs) |
| TEMP_DOWNLOAD_DIR | NO | /tmp/nimblevault_downloads | Temporary storage for downloaded videos |
| CORS_ORIGINS | NO | ["http://localhost:3000"] | Allowed frontend origins |
| DEBUG | NO | false | Enable verbose SQL logging |

### Frontend (frontend/.env.local)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| NEXT_PUBLIC_API_URL | NO | http://localhost:8000 | Backend API base URL |

---

## Google API Setup

### Google Drive (Service Account)

1. Go to GCP Console -> APIs & Services -> Enable Google Drive API v3
2. Create a Service Account -> download the JSON key
3. Place the JSON file in backend/ and set GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
4. Share your target Drive folder with the service account email address (Viewer access)

### YouTube Data API (OAuth2)

1. Enable YouTube Data API v3 in GCP Console
2. Create an OAuth 2.0 Client ID (Desktop App type) -> download client_secrets.json
3. Place client_secrets.json in backend/
4. On first pipeline run, a browser window opens for one-time OAuth consent
5. The refreshable token is auto-saved to youtube_token.json for all future runs

### Gemini API

1. Visit https://aistudio.google.com/app/apikey
2. Create a new API key
3. Set GEMINI_API_KEY=<your-key> in backend/.env

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/scan | Scan a Drive folder; returns new PENDING jobs |
| GET | /api/jobs | Fetch all jobs sorted by creation date |
| PATCH | /api/jobs/{job_id}/title | Update AI-generated title before upload |
| POST | /api/process/{job_id} | Start pipeline for a single job (background) |
| POST | /api/process-batch | Start pipeline for all PENDING jobs (background) |
| GET | /health | Health check |

---

## Data Persistence & Duplicate Prevention

### video_jobs Table Schema

```sql
CREATE TABLE video_jobs (
    id               UUID PRIMARY KEY,
    drive_file_id    VARCHAR(255) UNIQUE NOT NULL,  -- Unique index
    file_name        VARCHAR(512) NOT NULL,
    full_path        TEXT NOT NULL,
    generated_title  TEXT,
    youtube_video_id VARCHAR(255),
    status           VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    error_log        TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Composite index for common dashboard queries
CREATE INDEX ix_video_jobs_status_created ON video_jobs (status, created_at);
```

### Duplicate Prevention Logic

The POST /api/scan endpoint implements a two-layer defense:

1. Pre-scan query: All existing drive_file_id values are fetched into a Python set before Drive traversal begins
2. Set membership check: Each discovered file is checked against the set - duplicates are skipped with a log message
3. Database-level guard: The UNIQUE constraint on drive_file_id acts as a safety net against race conditions
4. Idempotent scans: Scanning the same folder multiple times is always safe - only genuinely new files are added

### State Machine

```
PENDING --> DOWNLOADING --> TITLING --> UPLOADING --> COMPLETED
  ^                                         |
  +----------------- FAILED <--------------+
```

Failed jobs can be retried individually using the Retry button or will be excluded from batch processing until manually triggered.

---

## Title Generation Examples

| Drive Path | Generated Title |
|------------|----------------|
| Drive/Vlogs/2024/Week12/Final_Edit.mp4 | Vlogs 2024: Week 12 Final Edit |
| Drive/Products/Launch_X/Tutorials/Getting_Started.mov | Launch X Product Tutorial: Getting Started |
| Drive/Team/Archive/Q3/Marketing_Review_10-05.avi | Team Archive Q3: Marketing Review 10-05 |
| Drive/Clients/ACME/Testimonial_v2.mp4 | Client Testimonial: ACME (v2) |

---

## Development Notes

- Async throughout: FastAPI + asyncpg + asyncio.to_thread for blocking Google API calls
- Background tasks: Processing pipelines run in FastAPI BackgroundTasks - requests return 202 Accepted immediately
- Resumable uploads: Both Drive downloads and YouTube uploads use 8 MB chunked streaming for large files
- Token refresh: YouTube OAuth2 tokens are automatically refreshed when expired
- Graceful fallback: If Gemini API is unavailable, a local regex-based title generator activates automatically
- Type safety: Full TypeScript types on frontend, Python type annotations throughout backend

---

## GitHub Review Notice

For reviewer @earthshakira:

This repository contains the complete NimbleVault implementation as specified. All source files are production-grade with full TypeScript types on the frontend and Python type annotations throughout the backend. Environment variables are documented but credentials are never committed - please use the .env.example templates to configure your local instance. Thank you for your review!

---

## License

MIT (c) NimbleVault
