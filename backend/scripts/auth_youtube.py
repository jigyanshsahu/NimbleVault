"""
NimbleVault – YouTube OAuth2 Authentication Helper
Runs a local browser flow to generate and persist `youtube_token.json`.
"""
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
from app.core.config import get_settings
from app.services.youtube_service import _persist_token

def authenticate():
    settings = get_settings()
    print("=" * 60)
    print(" NimbleVault - YouTube OAuth2 Authorization")
    print("=" * 60)
    print(f"Client secrets: {settings.YOUTUBE_CLIENT_SECRETS_JSON}")
    print(f"Token destination: {settings.YOUTUBE_TOKEN_JSON}")
    print(f"Scopes: {settings.YOUTUBE_SCOPES}")
    print("\nStarting local server and opening web browser for Google login...")
    print("If your browser doesn't open automatically, copy and paste the URL from below.\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        settings.YOUTUBE_CLIENT_SECRETS_JSON,
        settings.YOUTUBE_SCOPES,
    )
    
    # Try port 8080 first, fallback to dynamic port if busy
    try:
        creds = flow.run_local_server(port=8080, open_browser=True)
    except OSError:
        creds = flow.run_local_server(port=0, open_browser=True)

    _persist_token(creds)

    print(f"\n[OK] Token successfully saved to: {settings.YOUTUBE_TOKEN_JSON}")

    # Verify connection by reading channel info
    try:
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        channels = yt.channels().list(mine=True, part="snippet").execute()
        items = channels.get("items", [])
        if items:
            title = items[0]["snippet"]["title"]
            channel_id = items[0]["id"]
            print(f"[OK] Authorized YouTube Channel: '{title}' (ID: {channel_id})")
        else:
            print("[INFO] Successfully authenticated with Google, but no public channel found on this account.")
    except Exception as exc:
        print(f"[!] Authenticated, but could not fetch channel info: {exc}")

    print("\nYou can now execute the NimbleVault pipeline with full YouTube distribution!")

if __name__ == "__main__":
    authenticate()
