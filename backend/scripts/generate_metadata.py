"""
NimbleVault – Intelligent Metadata Generator CLI
Uses Google Gemini API to generate structured YouTube titles, descriptions,
and SEO tags from Google Drive file routes.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import logging
logging.getLogger("google").setLevel(logging.ERROR)
logging.getLogger("google_genai").setLevel(logging.ERROR)

from app.services.gemini_service import GeminiService, VideoMetadata
from app.services.drive_service import DriveService

DEFAULT_FOLDER_ID = "1HKD2on9LkF3OfKvWmkZwtdnSHMS1HUGs"


def print_metadata_card(path: str, meta: VideoMetadata):
    print("\n" + "=" * 70)
    print(f" FILE ROUTE: {path}")
    print("=" * 70)
    print(f"TITLE:       {meta.title}")
    print(f"CATEGORY:    {meta.category}")
    print(f"TAGS:        {', '.join(meta.tags)}")
    print("\nDESCRIPTION:")
    print("-" * 70)
    print(meta.description)
    print("-" * 70)


async def process_single_path(path: str, as_json: bool = False):
    gemini = GeminiService()
    meta = await gemini.generate_metadata(path)
    if as_json:
        print(json.dumps({"route": path, **meta.model_dump()}, indent=2))
    else:
        print_metadata_card(path, meta)


async def process_folder(folder_id: str, as_json: bool = False):
    try:
        drive = DriveService()
    except Exception as exc:
        print(f"\n[ERROR] Google Drive service initialization failed: {exc}")
        print("Please check that 'service_account.json' exists in backend/ with valid GCP credentials.\n")
        return

    gemini = GeminiService()

    print(f"Scanning Google Drive Folder ID: {folder_id}...")
    try:
        files = await drive.list_videos_recursive(folder_id)
    except Exception as exc:
        print(f"\n[ERROR] Google Drive folder scanning failed: {exc}\n")
        return
    print(f"Found {len(files)} video file route(s). Generating metadata with Gemini AI...\n")

    results = []
    for f in files:
        meta = await gemini.generate_metadata(f.full_path)
        if as_json:
            results.append({"route": f.full_path, **meta.model_dump()})
        else:
            print_metadata_card(f.full_path, meta)

    if as_json:
        print(json.dumps(results, indent=2))


async def main():
    parser = argparse.ArgumentParser(
        description="Generate rich YouTube titles & metadata from Google Drive file routes using Gemini AI"
    )
    parser.add_argument(
        "--path",
        type=str,
        help="Single Google Drive file route (e.g. Drive/Products/Launch_X/Tutorials/Getting_Started.mov)",
    )
    parser.add_argument(
        "--folder-id",
        type=str,
        help=f"Google Drive folder ID to scan and generate metadata for (default: {DEFAULT_FOLDER_ID})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw structured JSON instead of formatted text",
    )

    args = parser.parse_args()

    if args.path:
        await process_single_path(args.path, as_json=args.json)
    else:
        folder_id = args.folder_id or DEFAULT_FOLDER_ID
        await process_folder(folder_id, as_json=args.json)


if __name__ == "__main__":
    asyncio.run(main())
