from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from calendar_agent.store import get_valid_credentials, save_credentials

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


class CalendarNotConnectedError(RuntimeError):
    pass


def get_redirect_uri() -> str:
    return os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/api/calendar/callback")


def build_auth_flow() -> Flow:
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET must be set")

    redirect_uri = get_redirect_uri()
    if redirect_uri.startswith("http://"):
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
            "redirect_uris": [redirect_uri],
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)


def get_authorization_url() -> str:
    flow = build_auth_flow()
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return authorization_url


def exchange_code(project_root: Path, user_id: str, code: str):
    flow = build_auth_flow()
    flow.fetch_token(code=code)
    return save_credentials(project_root, user_id, flow.credentials)


def get_calendar_service(project_root: Path, user_id: str):
    credentials = get_valid_credentials(project_root, user_id, SCOPES)
    if not credentials:
        raise CalendarNotConnectedError("Google Calendar is not connected")
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def read_events(project_root: Path, user_id: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    service = get_calendar_service(project_root, user_id)
    result = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=20,
    ).execute()
    return result.get("items", [])


def format_events_for_voice(events: list[dict[str, Any]], label: str) -> str:
    if not events:
        return f"You have nothing on your calendar for {label}."

    count = len(events)
    opener = f"You have {count} event{'s' if count != 1 else ''} on your calendar for {label}."
    parts = []
    for event in events[:6]:
        title = event.get("summary") or "Untitled event"
        start = event.get("start", {})
        when = _format_start(start)
        parts.append(f"{when}, {title}")

    if count > 6:
        parts.append(f"and {count - 6} more")

    return f"{opener} " + "; ".join(parts) + "."


def _format_start(start: dict[str, Any]) -> str:
    if "date" in start:
        return "all day"

    raw = start.get("dateTime")
    if not raw:
        return "time unknown"

    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return "time unknown"

    return value.strftime("%-I:%M %p").lower()
