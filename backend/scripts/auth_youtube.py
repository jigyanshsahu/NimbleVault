"""
NimbleVault – YouTube OAuth2 Authentication Helper
Runs a local browser flow to generate and persist `youtube_token.json`
with robust validation and descriptive error diagnostics.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import get_settings
from app.services.youtube_service import _persist_token


def _validate_client_secrets_file(file_path: str) -> bool:
    """Validate client_secrets.json existence and schema."""
    if not os.path.exists(file_path):
        print(f"\n[ERROR] OAuth Client Secrets file not found at: '{file_path}'")
        print("\nTroubleshooting Steps:")
        print("1. Go to Google Cloud Console: https://console.cloud.google.com/apis/credentials")
        print("2. Click '+ CREATE CREDENTIALS' → 'OAuth client ID'.")
        print("3. Application type MUST be 'Desktop app' (not Service Account, not Web).")
        print(f"4. Download the JSON file and save it as '{file_path}' in the backend/ directory.")
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as err:
        print(f"\n[ERROR] Client secrets file '{file_path}' is corrupted or not valid JSON: {err}")
        return False
    except Exception as err:
        print(f"\n[ERROR] Could not read client secrets file '{file_path}': {err}")
        return False

    # Check for common user mistake: placing a Service Account key instead of OAuth client secrets
    if data.get("type") == "service_account":
        print(f"\n[ERROR] '{file_path}' contains a Google Service Account key, NOT an OAuth Client ID!")
        print("Service accounts cannot upload videos to individual YouTube channels.")
        print("You must download an 'OAuth 2.0 Client ID' of type 'Desktop App' from Google Cloud Console.")
        return False

    if "installed" not in data and "web" not in data:
        print(f"\n[ERROR] '{file_path}' does not contain 'installed' or 'web' OAuth client configuration.")
        print("Please ensure you downloaded the correct OAuth 2.0 Client ID JSON from GCP Console.")
        return False

    return True


def authenticate() -> bool:
    """
    Execute YouTube OAuth2 authorization flow with robust error handling.
    Returns True on success, False on failure.
    """
    settings = get_settings()
    print("=" * 65)
    print(" NIMBLEVAULT - YOUTUBE OAUTH2 AUTHORIZATION")
    print("=" * 65)
    print(f"Client secrets:    {settings.YOUTUBE_CLIENT_SECRETS_JSON}")
    print(f"Token destination: {settings.YOUTUBE_TOKEN_JSON}")
    print(f"Requested Scopes:  {', '.join(settings.YOUTUBE_SCOPES)}")

    # 1. Pre-flight check on client_secrets.json
    if not _validate_client_secrets_file(settings.YOUTUBE_CLIENT_SECRETS_JSON):
        return False

    print("\nStarting local authentication server and launching browser...")
    print("If your browser does not open automatically, copy and paste the URL shown below.\n")

    # 2. Build flow
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            settings.YOUTUBE_CLIENT_SECRETS_JSON,
            settings.YOUTUBE_SCOPES,
        )
    except Exception as exc:
        print(f"\n[ERROR] Failed to initialize Google OAuth flow: {exc}")
        return False

    # 3. Run local server for auth callback
    creds = None
    try:
        # Try port 8080 first; fallback to automatic dynamic port (port 0)
        try:
            creds = flow.run_local_server(port=8080, open_browser=True)
        except (OSError, socket_error if "socket_error" in dir() else Exception):
            print("[INFO] Port 8080 unavailable or busy. Falling back to dynamic local port...")
            creds = flow.run_local_server(port=0, open_browser=True)
    except KeyboardInterrupt:
        print("\n[!] Authorization cancelled by user (KeyboardInterrupt).")
        return False
    except Exception as exc:
        print(f"\n[ERROR] OAuth browser authorization failed: {exc}")
        print("Tip: If running on a headless server without a browser, run on a local machine first")
        print("and copy the resulting 'youtube_token.json' to this directory.")
        return False

    if not creds:
        print("\n[ERROR] No credentials returned from authorization server.")
        return False

    # 4. Persist token
    try:
        _persist_token(creds)
        print(f"\n[OK] OAuth token successfully saved to: {settings.YOUTUBE_TOKEN_JSON}")
    except Exception as exc:
        print(f"\n[ERROR] Failed to write token to '{settings.YOUTUBE_TOKEN_JSON}': {exc}")
        return False

    # 5. Verify credentials by retrieving YouTube channel information
    print("\nVerifying YouTube API connectivity and channel access...")
    try:
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        channels_resp = yt.channels().list(mine=True, part="snippet,statistics").execute()
        items = channels_resp.get("items", [])
        if items:
            snippet = items[0].get("snippet", {})
            title = snippet.get("title", "Untitled Channel")
            channel_id = items[0].get("id", "Unknown ID")
            custom_url = snippet.get("customUrl", "")
            stats = items[0].get("statistics", {})
            subs = stats.get("subscriberCount", "Hidden")
            video_cnt = stats.get("videoCount", "0")

            print(f"[OK] Successfully verified YouTube Channel:")
            print(f"     * Channel Title: '{title}'")
            print(f"     * Channel ID:    {channel_id}")
            if custom_url:
                print(f"     * Custom Handle: {custom_url}")
            print(f"     * Current Videos:{video_cnt} | Subscribers: {subs}")
        else:
            print("[INFO] Authenticated with Google successfully, but no YouTube channel was found on this Google account.")
            print("       To create a channel: Visit https://www.youtube.com/create_channel")
    except HttpError as http_err:
        status_code = getattr(http_err.resp, "status", 0)
        error_details = str(http_err)
        if "insufficientPermissions" in error_details:
            print("[OK] YouTube OAuth credentials verified for video uploads (`youtube.upload`).")
        elif status_code == 403 and "accessNotConfigured" in error_details:
            print("\n[ERROR] YouTube Data API v3 is not enabled in your Google Cloud Project!")
            print("Enable it here: https://console.cloud.google.com/apis/library/youtube.googleapis.com")
        elif status_code == 403 and "quotaExceeded" in error_details:
            print("\n[WARN] YouTube API daily quota exceeded for this Google Cloud project.")
        else:
            print(f"\n[WARN] Authenticated, but could not query channel metadata (HTTP {status_code}): {http_err}")
    except Exception as exc:
        print(f"\n[WARN] Authenticated, but could not fetch channel metadata: {exc}")

    print("\n" + "=" * 65)
    print(" AUTHORIZATION COMPLETE")
    print(" You can now execute the NimbleVault pipeline with live YouTube uploads!")
    print(" Example: python scripts/run_pipeline.py --folder-id <FOLDER_ID>")
    print("=" * 65 + "\n")
    return True


def check_status() -> bool:
    """Check existing YouTube authorization status and display channel info."""
    import google.oauth2.credentials
    from google.auth.transport.requests import Request

    settings = get_settings()
    token_path = settings.YOUTUBE_TOKEN_JSON
    print("=" * 65)
    print(" NIMBLEVAULT - YOUTUBE AUTHENTICATION STATUS CHECK")
    print("=" * 65)

    if not os.path.exists(token_path):
        print(f"[STATUS] No YouTube token found at '{token_path}'.")
        print("         Run 'python scripts/auth_youtube.py' to authenticate.\n")
        return False

    try:
        with open(token_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        creds = google.oauth2.credentials.Credentials.from_authorized_user_info(
            data, settings.YOUTUBE_SCOPES
        )
        if creds and creds.expired and creds.refresh_token:
            print("[INFO] Token expired, refreshing credentials...")
            creds.refresh(Request())
            _persist_token(creds)
            print("[OK]   Token successfully refreshed.")

        if not creds or not creds.valid:
            print("[STATUS] Token is invalid or revoked.")
            print("         Run 'python scripts/auth_youtube.py' to re-authenticate.\n")
            return False

        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        try:
            channels_resp = yt.channels().list(mine=True, part="snippet,statistics").execute()
            items = channels_resp.get("items", [])
            if items:
                snippet = items[0].get("snippet", {})
                title = snippet.get("title", "Untitled Channel")
                channel_id = items[0].get("id", "Unknown ID")
                stats = items[0].get("statistics", {})
                video_cnt = stats.get("videoCount", "0")
                print(f"[OK]   YouTube Token is VALID and active!")
                print(f"       * Channel: '{title}' (ID: {channel_id})")
                print(f"       * Uploaded Videos: {video_cnt}")
            else:
                print("[OK]   YouTube Token is VALID, but no channel found on this account.")
        except HttpError as ch_err:
            if "insufficientPermissions" in str(ch_err):
                print("[OK]   YouTube OAuth Token is VALID and active!")
                print("       * Authorized Scope: youtube.upload (Dedicated video upload credentials)")
                print("       * Status: Ready for pipeline uploads")
            else:
                print(f"[WARN] YouTube Token active, but channel check returned HTTP {getattr(ch_err.resp, 'status', 0)}: {ch_err}")

        print("=" * 65 + "\n")
        return True
    except Exception as exc:
        print(f"[ERROR] Failed to verify YouTube token: {exc}\n")
        return False


if __name__ == "__main__":
    if "--check" in sys.argv or "-c" in sys.argv:
        success = check_status()
    else:
        success = authenticate()
    sys.exit(0 if success else 1)
