# 🏛️ NimbleVault — CLI Commands Reference

> All commands must be run from the `backend/` directory with the virtual environment activated.

---

## 📋 Table of Contents

- [Setup Commands](#setup-commands)
- [Pipeline Commands (`run_pipeline.py`)](#pipeline-commands)
- [YouTube Authentication (`auth_youtube.py`)](#youtube-authentication)
- [Metadata Generator (`generate_metadata.py`)](#metadata-generator)
- [Demo (`demo.py`)](#demo)

---

## Setup Commands

| #  | Command                                        | Description                            |
|----|------------------------------------------------|----------------------------------------|
| 1  | `python -m venv venv`                          | Create a virtual environment           |
| 2  | `.\venv\Scripts\Activate.ps1` *(Windows)*      | Activate virtual environment           |
| 2  | `source venv/bin/activate` *(Linux/macOS)*      | Activate virtual environment           |
| 3  | `pip install -r requirements.txt`              | Install all Python dependencies        |
| 4  | `Copy-Item .env.example .env` *(Windows)*      | Create `.env` config from template     |
| 4  | `cp .env.example .env` *(Linux/macOS)*          | Create `.env` config from template     |

---

## Pipeline Commands

**Script:** `scripts/run_pipeline.py`

### Flags

| Flag               | Type     | Description                                                                                  |
|--------------------|----------|----------------------------------------------------------------------------------------------|
| `--folder-id ID`   | `string` | Google Drive folder ID to scan (or set `GOOGLE_DRIVE_FOLDER_ID` in `.env`)                   |
| `--demo`           | `flag`   | Run the zero-credential interactive reviewer demo across all 4 rubric scenarios              |
| `--status`         | `flag`   | Audit YouTube liveness and display the status table of all tracked video jobs                 |
| `--sync`           | `flag`   | Full sync: scan Google Drive nested folders, audit YouTube liveness, and show status table    |
| `--scan`           | `flag`   | When used with `--status`, also scan Google Drive before displaying status                    |
| `--scan-only`      | `flag`   | Only perform Google Drive acquisition, YouTube audit, and show status table (no uploads)      |
| `--dry-run`        | `flag`   | Run Drive download and Gemini AI titling, but simulate the YouTube upload                     |
| `--batch`          | `flag`   | Process all pending jobs already stored in the database                                       |
| `--job-id ID`      | `string` | Execute pipeline for a specific existing Job ID                                               |
| `--force`          | `flag`   | Force re-processing of all video files in folder (resets existing jobs to `PENDING`)          |

### Usage Examples

```bash
# 1. Run the zero-credential demo (no API keys needed)
python scripts/run_pipeline.py --demo

# 2. Check system readiness & view all tracked jobs
python scripts/run_pipeline.py --status

# 3. Dry run — real Drive download + Gemini titling, simulated YouTube upload
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --dry-run

# 4. Live pipeline — full end-to-end with real YouTube upload ⭐⭐
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID

# 5. Scan only — discover and index videos without processing
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --scan-only

# 6. Batch process — process all pending jobs in the database
python scripts/run_pipeline.py --batch

# 7. Full sync — scan Drive for new content + reconcile YouTube records
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --sync

# 8. Force reprocess — reset completed jobs back to PENDING
python scripts/run_pipeline.py --folder-id YOUR_FOLDER_ID --force

# 9. Run a specific job by ID
python scripts/run_pipeline.py --job-id JOB_UUID

# 10. Status with Drive scan
python scripts/run_pipeline.py --status --scan --folder-id YOUR_FOLDER_ID
```

---

## YouTube Authentication

**Script:** `scripts/auth_youtube.py`

### Flags

| Flag              | Type   | Description                                            |
|-------------------|--------|--------------------------------------------------------|
| `--check` / `-c`  | `flag` | Verify current YouTube OAuth2 token status             |
| *(no flags)*       | —      | Run interactive browser-based OAuth2 authentication    |

### Usage Examples

```bash
# Authenticate YouTube (opens browser for OAuth2 consent)
python scripts/auth_youtube.py

# Check if the existing token is valid
python scripts/auth_youtube.py --check
```

---

## Metadata Generator

**Script:** `scripts/generate_metadata.py`

### Flags

| Flag               | Type     | Description                                                                              |
|--------------------|----------|------------------------------------------------------------------------------------------|
| `--path PATH`      | `string` | Single Google Drive file route (e.g. `Drive/Products/Launch_X/Tutorials/Getting_Started.mov`) |
| `--folder-id ID`   | `string` | Google Drive folder ID to scan and generate metadata for                                 |
| `--json`           | `flag`   | Output raw structured JSON instead of formatted text                                     |

### Usage Examples

```bash
# Generate metadata for a single file path
python scripts/generate_metadata.py --path "Drive/Vlogs/2024/Week12/Final_Edit.mp4"

# Generate metadata for all videos in a Drive folder
python scripts/generate_metadata.py --folder-id YOUR_FOLDER_ID

# Output as structured JSON
python scripts/generate_metadata.py --path "Drive/Tutorials/Intro.mp4" --json

# Scan a folder and output JSON
python scripts/generate_metadata.py --folder-id YOUR_FOLDER_ID --json
```

---

## Demo

**Script:** `scripts/demo.py`

### Usage

```bash
# Run the zero-credential reviewer demo (no flags needed)
python scripts/demo.py
```

> **No API keys, cloud accounts, or network access required.** Demonstrates all 4 benchmark scenarios:
> 1. Mass Content Acquisition (recursive Drive traversal simulation)
> 2. Intelligent Metadata Generation (deterministic fallback engine)
> 3. Seamless Distribution (simulated YouTube resumable upload)
> 4. Idempotency & State Tracking (state machine lifecycle)

---

## Quick Reference

| Purpose                          | Command                                                              |
|----------------------------------|----------------------------------------------------------------------|
| **Run demo** (zero credentials)  | `python scripts/demo.py`                                             |
| **Run demo** via pipeline CLI    | `python scripts/run_pipeline.py --demo`                              |
| **Check system readiness**       | `python scripts/run_pipeline.py --status`                            |
| **Authenticate YouTube**         | `python scripts/auth_youtube.py`                                     |
| **Verify YouTube auth**          | `python scripts/auth_youtube.py --check`                             |
| **Scan only** (no processing)    | `python scripts/run_pipeline.py --folder-id ID --scan-only`          |
| **Dry run** (simulated upload)   | `python scripts/run_pipeline.py --folder-id ID --dry-run`            |
| **Live pipeline**                | `python scripts/run_pipeline.py --folder-id ID`                      |
| **Process pending jobs**         | `python scripts/run_pipeline.py --batch`                             |
| **Sync Drive + YouTube**         | `python scripts/run_pipeline.py --folder-id ID --sync`               |
| **Force reprocessing**           | `python scripts/run_pipeline.py --folder-id ID --force`              |
| **Generate metadata** (single)   | `python scripts/generate_metadata.py --path "Drive/.../file.mp4"`    |
| **Generate metadata** (folder)   | `python scripts/generate_metadata.py --folder-id ID`                 |
| **Generate metadata** (JSON)     | `python scripts/generate_metadata.py --folder-id ID --json`          |
