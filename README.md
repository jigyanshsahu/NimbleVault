# NimbleVault --- AI-Powered Video Content Automation

NimbleVault is a Python-based backend automation platform that processes
video files stored in Google Drive and publishes them to YouTube with
automatically generated metadata.

The system combines Google Drive, Google Gemini AI, YouTube Data API v3,
and SQLite to provide an automated content-processing pipeline with
persistent job tracking, resumable uploads, retry handling, and state
reconciliation.

------------------------------------------------------------------------

## Table of Contents

-   [Overview](#overview)
-   [Key Features](#key-features)
-   [Architecture](#architecture)
-   [Technology Stack](#technology-stack)
-   [Project Structure](#project-structure)
-   [Prerequisites](#prerequisites)
-   [Installation](#installation)
-   [Configuration](#configuration)
-   [Google API Setup](#google-api-setup)
-   [YouTube Authentication](#youtube-authentication)
-   [Running the Application](#running-the-application)
-   [Processing Workflow](#processing-workflow)
-   [Database and State Management](#database-and-state-management)
-   [Metadata Generation](#metadata-generation)
-   [Reliability and Error Handling](#reliability-and-error-handling)
-   [Design Decisions](#design-decisions)
-   [Performance Considerations](#performance-considerations)
-   [Security Considerations](#security-considerations)
-   [Troubleshooting](#troubleshooting)
-   [Useful Commands](#useful-commands)
-   [Reviewer Quick Start](#reviewer-quick-start)

------------------------------------------------------------------------

## Overview

NimbleVault automates this workflow:

``` text
Google Drive
     │
     │ Recursive discovery
     ▼
NimbleVault
     │
     ├── Download video
     ├── Generate metadata with Gemini
     ├── Persist job state in SQLite
     └── Upload using YouTube Data API
                │
                ▼
           YouTube Channel
```

The application is intentionally implemented as a backend automation
system and CLI rather than a web application. This keeps the execution
environment lightweight and makes the pipeline suitable for local
execution, scheduled jobs, automation servers, and command-line
workflows.

------------------------------------------------------------------------

## Key Features

### Google Drive Integration

-   Recursive traversal of nested Google Drive folders.
-   Detection of supported video files.
-   Preservation of the video's virtual Drive path.
-   Google Service Account authentication.
-   Paginated Drive API requests.
-   Protection against repeated/circular folder traversal.
-   Chunked video downloads.
-   Temporary-file cleanup after processing.

### AI Metadata Generation

Gemini AI is used to generate contextual YouTube metadata from the
video's Drive path and available context.

The metadata engine can generate:

-   Video title
-   Description
-   SEO tags/hashtags
-   YouTube category

A deterministic fallback mechanism is available when Gemini is
unavailable, rate-limited, or not configured.

### YouTube Uploading

-   OAuth 2.0 authentication.
-   Resumable uploads.
-   Chunked file transmission.
-   Retry handling for transient API/network errors.
-   Configurable YouTube privacy status.
-   Configurable fallback category.
-   Title length handling.
-   YouTube video liveness checks.

### Persistent Processing State

SQLite stores the state of tracked video jobs and provides:

-   Duplicate prevention
-   Processing history
-   Failure tracking
-   Retry support
-   YouTube video ID storage
-   Self-healing reconciliation

------------------------------------------------------------------------

## Architecture

``` text
┌─────────────────────────────────────────────────────────────┐
│                       Google Drive                          │
│                                                             │
│      Nested folders containing video files                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ 1. Recursive discovery
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    NimbleVault Engine                       │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Google Drive    │  │ Gemini AI       │  │ YouTube     │ │
│  │ Service         │  │ Metadata        │  │ Service     │ │
│  │                 │  │ Engine          │  │             │ │
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘ │
│           │                    │                  │         │
│           └────────────────────┼──────────────────┘         │
│                                │                            │
│                         ┌──────▼──────┐                     │
│                         │ SQLite DB   │                     │
│                         │ State/Jobs  │                     │
│                         └─────────────┘                     │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ 2. Resumable upload
                             ▼
                    ┌──────────────────┐
                    │     YouTube      │
                    │     Channel      │
                    └──────────────────┘
```

------------------------------------------------------------------------

## Technology Stack

  Component                Technology
  ------------------------ --------------------------
  Language                 Python
  Database                 SQLite
  Async Database Driver    aiosqlite
  Configuration            pydantic-settings
  AI Metadata              Google Gemini API
  Cloud Storage            Google Drive API v3
  Video Distribution       YouTube Data API v3
  Drive Authentication     Google Service Account
  YouTube Authentication   OAuth 2.0
  Interface                Python CLI
  Upload Strategy          Resumable/chunked upload

------------------------------------------------------------------------

## Project Structure

``` text
nimblevault/
│
├── README.md
│
└── backend/
    │
    ├── app/
    │   ├── core/
    │   │   ├── config.py
    │   │   └── database.py
    │   │
    │   ├── models/
    │   │   └── video.py
    │   │
    │   └── services/
    │       ├── drive_service.py
    │       ├── gemini_service.py
    │       └── youtube_service.py
    │
    ├── scripts/
    │   ├── run_pipeline.py
    │   ├── demo.py
    │   ├── auth_youtube.py
    │   └── generate_metadata.py
    │
    ├── requirements.txt
    ├── .env.example
    ├── .env
    ├── service_account.json
    ├── client_secrets.json
    └── youtube_token.json
```

> Credential files and `.env` contain sensitive information and should
> not be committed to a public repository.

------------------------------------------------------------------------

## Prerequisites

Before installing NimbleVault, ensure that the following are available:

-   Python 3.10 or newer
-   Git
-   A Google account
-   A Google Cloud project for live Google integrations
-   A Google Drive folder containing the videos to process
-   A YouTube channel for live uploads
-   A Gemini API key for AI-generated metadata

The local demonstration does **not** require Google API credentials.

------------------------------------------------------------------------

## Installation

### 1. Open the project

From a terminal:

``` bash
cd nimblevault
cd backend
```

### 2. Create a virtual environment

``` bash
python -m venv venv
```

#### Windows PowerShell

``` powershell
.\venv\Scripts\Activate.ps1
```

#### Linux / macOS

``` bash
source venv/bin/activate
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

### 4. Create the environment file

#### Windows PowerShell

``` powershell
Copy-Item .env.example .env
```

#### Linux / macOS

``` bash
cp .env.example .env
```

------------------------------------------------------------------------

## Configuration

The `.env` file contains runtime configuration.

Example:

``` env
DATABASE_URL=sqlite+aiosqlite:///nimblevault.db

GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json

YOUTUBE_CLIENT_SECRETS_JSON=client_secrets.json
YOUTUBE_TOKEN_JSON=youtube_token.json

YOUTUBE_PRIVACY_STATUS=private
YOUTUBE_VIDEO_CATEGORY_ID=22

GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite

TEMP_DOWNLOAD_DIR=downloads/temp
```

### Configuration Reference

  -----------------------------------------------------------------------
  Variable                            Purpose
  ----------------------------------- -----------------------------------
  `DATABASE_URL`                      SQLite database location

  `GOOGLE_SERVICE_ACCOUNT_JSON`       Google Drive Service Account
                                      credentials

  `YOUTUBE_CLIENT_SECRETS_JSON`       YouTube OAuth client credentials

  `YOUTUBE_TOKEN_JSON`                Persisted YouTube OAuth token

  `YOUTUBE_PRIVACY_STATUS`            Default YouTube privacy setting

  `YOUTUBE_VIDEO_CATEGORY_ID`         Fallback YouTube category

  `GEMINI_API_KEY`                    Gemini API authentication

  `GEMINI_MODEL`                      Gemini model used for metadata
                                      generation

  `TEMP_DOWNLOAD_DIR`                 Temporary local video storage
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## Google API Setup

Live execution requires three integrations:

1.  Gemini API
2.  Google Drive API
3.  YouTube Data API v3

### 1. Gemini API

1.  Open https://aistudio.google.com/
2.  Sign in.
3.  Create an API key.
4.  Copy the key.
5.  Open `backend/.env`.
6.  Set:

``` env
GEMINI_API_KEY=YOUR_REAL_API_KEY
```

Keep the key private.

### 2. Google Drive API

NimbleVault uses a Google Service Account to read the configured Drive
folder.

#### Create/select a Google Cloud project

Open https://console.cloud.google.com/ and create or select a project.

#### Enable Google Drive API

Navigate to:

``` text
APIs & Services
→ Library
→ Google Drive API
→ Enable
```

#### Create a Service Account

Navigate to:

``` text
APIs & Services
→ Credentials
→ Create Credentials
→ Service Account
```

Create an account such as:

``` text
drive-robot
```

#### Create the JSON key

Open the Service Account:

``` text
Keys
→ Add Key
→ Create New Key
→ JSON
```

Download the file, rename it:

``` text
service_account.json
```

and place it at:

``` text
backend/service_account.json
```

#### Share the target Drive folder

Open `service_account.json` and find:

``` json
"client_email": "..."
```

Copy the email address.

In Google Drive:

1.  Right-click the target video folder.
2.  Select **Share**.
3.  Add the Service Account email.
4.  Grant **Viewer** permission.
5.  Save.

### 3. YouTube Data API v3

#### Enable the API

In Google Cloud Console:

``` text
APIs & Services
→ Library
→ YouTube Data API v3
→ Enable
```

#### Configure OAuth

Configure the OAuth consent screen and use an application name such as:

``` text
NimbleVault
```

If the application is configured for external testing, add the Google
account that will authorize the application as a test user.

> Google Cloud's interface may change. Follow the current labels
> displayed in the console.

#### Create an OAuth client

Navigate to:

``` text
APIs & Services
→ Credentials
→ Create Credentials
→ OAuth Client ID
```

Select:

``` text
Desktop app
```

Create the client and download its JSON credentials.

Rename the file:

``` text
client_secrets.json
```

Place it at:

``` text
backend/client_secrets.json
```

------------------------------------------------------------------------

## YouTube Authentication

From the `backend` directory:

``` bash
python scripts/auth_youtube.py
```

A browser window will open.

1.  Select the Google account associated with the YouTube channel.
2.  Complete the authorization flow.
3.  Grant the requested permissions.

After successful authentication, the application stores:

``` text
youtube_token.json
```

Keep this file private.

To verify authorization:

``` bash
python scripts/auth_youtube.py --check
```

------------------------------------------------------------------------

## Running the Application

### 1. Demo Mode

The project provides a zero-credential demonstration.

``` bash
python scripts/run_pipeline.py --demo
```

or:

``` bash
python scripts/demo.py
```

Demo mode is intended for local verification and reviewer evaluation
without requiring Google Drive, Gemini, or YouTube credentials.

### 2. Status Check

``` bash
python scripts/run_pipeline.py --status
```

Use this to inspect system readiness and tracked video jobs.

### 3. Dry Run

Before the first live upload, use:

``` bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --dry-run
```

For a Drive URL such as:

``` text
https://drive.google.com/drive/folders/1AbCdEfGh123
```

the folder ID is:

``` text
1AbCdEfGh123
```

Dry-run mode tests the real Drive workflow and metadata processing while
simulating the YouTube upload.

### 4. Live Pipeline

After a successful dry run:

``` bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID
```

The configured YouTube privacy setting is controlled by:

``` env
YOUTUBE_PRIVACY_STATUS=private
```

Verify this setting before a live run.

### 5. Scan Only

``` bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --scan-only
```

This discovers and indexes videos without triggering the full
processing/upload workflow.

### 6. Batch Processing

``` bash
python scripts/run_pipeline.py --batch
```

Processes pending jobs already stored in the database.

### 7. Synchronization

``` bash
python scripts/run_pipeline.py --sync
```

Scans Drive for new content and reconciles existing YouTube records.

### 8. Force Reprocessing

``` bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --force
```

Use this carefully because existing jobs can be processed again.

------------------------------------------------------------------------

## Processing Workflow

A normal pipeline execution follows:

``` text
1. Select Google Drive folder
             ↓
2. Recursively discover folders/files
             ↓
3. Identify supported video files
             ↓
4. Check database state
             ↓
5. Download video in chunks
             ↓
6. Generate YouTube metadata
             ↓
7. Store/update job state
             ↓
8. Upload using resumable upload
             ↓
9. Store YouTube video information
             ↓
10. Mark job COMPLETED
```

The Drive path is preserved as contextual information for metadata
generation.

------------------------------------------------------------------------

## Database and State Management

NimbleVault uses SQLite through `aiosqlite`.

A simplified state machine is:

``` text
PENDING
   ↓
DOWNLOADING
   ↓
TITLING
   ↓
UPLOADING
   ↓
COMPLETED
```

A failed operation can result in:

``` text
FAILED
```

The database provides:

-   Duplicate prevention
-   Persistent processing state
-   Failure tracking
-   Retry support
-   YouTube video ID storage
-   Reconciliation with external YouTube state

### Why SQLite?

SQLite was selected because the project is designed as a lightweight
automation engine. It requires no separate database server and provides
persistent local state.

------------------------------------------------------------------------

## Metadata Generation

The metadata service uses the Drive file path and contextual information
to generate:

-   Title
-   Description
-   Tags/hashtags
-   YouTube category

Example input:

``` text
Drive/Products/Launch_X/Tutorials/Getting_Started.mov
```

The resulting metadata can use the folder and filename context to
identify the subject of the video.

A deterministic fallback engine is available when Gemini is unavailable,
rate-limited, or not configured. This prevents the entire pipeline from
depending exclusively on the external AI service.

------------------------------------------------------------------------

## Reliability and Error Handling

### Resumable uploads

YouTube uploads use resumable upload sessions so large files can be
transferred more reliably.

### Chunked processing

Videos are transferred in chunks instead of loading the entire file into
memory.

### Retry handling

Transient API and network failures are handled using retry logic for
appropriate temporary errors.

### Temporary file cleanup

Temporary downloaded files are cleaned up after processing to prevent
unnecessary disk usage.

### Self-healing reconciliation

When an existing YouTube upload is no longer available, the application
can reconcile its database record back to a pending state, making the
video eligible for processing again.

------------------------------------------------------------------------

## Design Decisions

### Backend CLI instead of a web UI

NimbleVault is intentionally a backend automation engine.

A CLI provides:

-   Simple deployment
-   Low infrastructure overhead
-   Easy local execution
-   Compatibility with scheduled jobs
-   Clear automation workflows

### Service abstraction

External integrations are isolated into:

``` text
drive_service.py
gemini_service.py
youtube_service.py
```

This separates provider-specific logic from pipeline orchestration and
improves maintainability.

### Persistent job state

Video jobs are stored in SQLite so the system can track:

-   Previously processed files
-   Failures
-   YouTube IDs
-   Processing states
-   External state reconciliation

### Deterministic AI fallback

Gemini improves metadata quality, but the pipeline retains deterministic
fallback behavior so temporary AI service failures do not necessarily
stop metadata generation.

### Chunked and resumable transfers

Large video files should not require the entire file to remain in
memory. Chunked downloads and resumable uploads reduce memory pressure
and improve resilience.

------------------------------------------------------------------------

## Performance Considerations

### Drive traversal

Folder/file traversal is designed to process discovered resources
without unnecessary repeated traversal.

The intended traversal complexity is approximately:

``` text
O(N)
```

where `N` is the number of folders/files encountered.

### Memory usage

Videos are processed using chunked transfers rather than loading the
complete file into memory. This keeps memory usage approximately
independent of total video size during streaming operations.

------------------------------------------------------------------------

## Security Considerations

The following files contain credentials or tokens and should never be
committed to a public repository:

``` text
.env
service_account.json
client_secrets.json
youtube_token.json
```

Use `.gitignore` to exclude them.

Never hard-code real API keys into source code.

If a credential is accidentally exposed:

1.  Revoke or rotate it in the relevant Google service.
2.  Replace the credential locally.
3.  Remove the secret from future commits.

------------------------------------------------------------------------

## Troubleshooting

### Google Drive: `403 Access Denied`

**Cause:** The Service Account does not have access to the target
folder.

**Solution:**

1.  Open `service_account.json`.
2.  Copy `client_email`.
3.  Open the target Drive folder.
4.  Share it with that email.
5.  Grant Viewer access.
6.  Run the pipeline again.

### YouTube: `403 quotaExceeded`

**Cause:** The Google Cloud project has reached its available YouTube
API quota.

**Solution:** Use dry-run mode for testing:

``` bash
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --dry-run
```

For live execution, review the project's quota information in Google
Cloud Console.

### YouTube authentication fails

Verify that:

-   `client_secrets.json` exists in `backend/`.
-   YouTube Data API v3 is enabled.
-   OAuth configuration is complete.
-   The authorizing Google account is permitted.
-   The command is being run from `backend/`.

Then retry:

``` bash
python scripts/auth_youtube.py
```

### Gemini metadata generation fails

Verify:

``` env
GEMINI_API_KEY=YOUR_REAL_API_KEY
```

Also verify that the configured model is available to the API account.

The deterministic fallback can be used when Gemini is unavailable.

### Python dependency errors

Make sure the virtual environment is active and reinstall:

``` bash
pip install -r requirements.txt
```

Check the Python version:

``` bash
python --version
```

------------------------------------------------------------------------

## Useful Commands

  -------------------------------------------------------------------------------------------------------------
  Purpose                             Command
  ----------------------------------- -------------------------------------------------------------------------
  Run demo                            `python scripts/demo.py`

  Run demo through CLI                `python scripts/run_pipeline.py --demo`

  Check status/readiness              `python scripts/run_pipeline.py --status`

  Check YouTube authorization         `python scripts/auth_youtube.py --check`

  Synchronize Drive/YouTube state     `python scripts/run_pipeline.py --sync`

  Scan only                           `python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --scan-only`

  Dry run                             `python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --dry-run`

  Live pipeline                       `python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID`

  Process pending jobs                `python scripts/run_pipeline.py --batch`

  Force reprocessing                  `python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --force`
  -------------------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## Reviewer Quick Start

For a reviewer who only needs to verify the project locally, no cloud
credentials are required for the demonstration.

From the repository root:

``` bash
cd backend
```

Create and activate the environment:

``` bash
python -m venv venv
```

Windows:

``` powershell
.\venv\Scripts\Activate.ps1
```

Linux/macOS:

``` bash
source venv/bin/activate
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

Run the demonstration:

``` bash
python scripts/run_pipeline.py --demo
```

or:

``` bash
python scripts/demo.py
```

This provides a local execution path for evaluating the application's
pipeline behavior without requiring Google Cloud, Google Drive, Gemini,
or YouTube credentials.

------------------------------------------------------------------------

## Summary

NimbleVault is a backend automation engine built around four core
responsibilities:

``` text
Google Drive
     ↓
Content Discovery
     ↓
AI Metadata Generation
     ↓
YouTube Upload
     ↓
Persistent State & Reconciliation
```

The architecture separates external service integrations from the core
pipeline, uses SQLite for persistent job tracking, provides
deterministic metadata fallback behavior, and uses chunked/resumable
transfers for large video files.

For the fastest local verification:

``` bash
cd backend
python scripts/run_pipeline.py --demo
```

For a real workflow, configure the required Google credentials, test
with `--dry-run`, and then execute the live pipeline with the target
Google Drive folder ID.
