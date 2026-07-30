# src/setup_youtube_auth.py
"""
YouTube Data API v3 OAuth 2.0 Interactive Setup Script
Automatically creates client_secrets.json from your Client ID and Client Secret,
then opens your browser to authenticate your YouTube channel and save token.json!
"""
import os
import sys
import json
import argparse
from pathlib import Path

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    print("[ERROR] Google API auth libraries not installed.")
    print("To install, run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
    sys.exit(1)

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def create_client_secrets_file(client_id, client_secret):
    secrets_path = Path("client_secrets.json")
    data = {
        "installed": {
            "client_id": client_id.strip(),
            "project_id": "youtube-automation-shorts",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret.strip(),
            "redirect_uris": ["http://localhost"]
        }
    }
    with open(secrets_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"[SUCCESS] Generated {secrets_path} successfully!")
    return secrets_path


def authenticate_youtube(client_id=None, client_secret=None):
    creds = None
    token_path = Path("token.json")
    secrets_path = Path("client_secrets.json")

    if client_id and client_secret:
        create_client_secrets_file(client_id, client_secret)

    if token_path.exists():
        print(f"[INFO] Found existing {token_path}. Verifying token...")
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("[INFO] Refreshing expired OAuth token...")
            creds.refresh(Request())
        else:
            if not secrets_path.exists():
                print("[ERROR] 'client_secrets.json' not found in project root.")
                print("\nLet's create it now from your Google Cloud Console credentials!")
                cid = input("Enter your Google OAuth Client ID: ").strip()
                csec = input("Enter your Google OAuth Client Secret: ").strip()
                if not cid or not csec:
                    print("[ERROR] Both Client ID and Client Secret are required!")
                    return False
                create_client_secrets_file(cid, csec)

            print("[INFO] Starting OAuth 2.0 local server on port 8080...")
            sys.stdout.flush()
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            print("\n" + "="*70)
            print("[INFO] CLICK OR COPY/PASTE THIS URL INTO YOUR BROWSER TO AUTHORIZE:")
            print(f"\n{auth_url}\n")
            print("="*70 + "\n")
            sys.stdout.flush()

            try:
                import webbrowser
                webbrowser.open(auth_url)
            except Exception:
                pass

            creds = flow.run_local_server(port=8080, open_browser=True)

        with open(token_path, "w") as token:
            token.write(creds.to_json())
            print(f"[SUCCESS] Saved OAuth credentials to {token_path}!")
            sys.stdout.flush()

    print("[SUCCESS] YouTube OAuth Authentication SUCCESSFUL! Your channel is ready for automatic publishing.")
    sys.stdout.flush()
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube OAuth Setup Script")
    parser.add_argument("--client-id", help="Google OAuth Client ID")
    parser.add_argument("--client-secret", help="Google OAuth Client Secret")
    args = parser.parse_args()

    authenticate_youtube(client_id=args.client_id, client_secret=args.client_secret)
