from __future__ import annotations

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

TOKEN_ENV = "GOOGLE_CALENDAR_TOKEN_JSON"
TOKEN_PATH_ENV = "GOOGLE_CALENDAR_TOKEN_PATH"


def token_path(project_root: Path, user_id: str) -> Path:
    configured = os.getenv(TOKEN_PATH_ENV)
    if configured:
        return Path(configured).expanduser()
    return project_root / "users" / user_id / "google_calendar_token.json"


def load_credentials(project_root: Path, user_id: str, scopes: list[str]) -> Credentials | None:
    token_json = os.getenv(TOKEN_ENV)
    if token_json:
        try:
            return Credentials.from_authorized_user_info(json.loads(token_json), scopes=scopes)
        except Exception as err:
            print(f"[calendar] Failed to load {TOKEN_ENV}: {err}")
            return None

    path = token_path(project_root, user_id)
    if not path.exists():
        return None

    try:
        return Credentials.from_authorized_user_file(str(path), scopes=scopes)
    except Exception as err:
        print(f"[calendar] Failed to load token file {path}: {err}")
        return None


def save_credentials(project_root: Path, user_id: str, credentials: Credentials) -> Path:
    path = token_path(project_root, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(credentials.to_json(), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def get_valid_credentials(project_root: Path, user_id: str, scopes: list[str]) -> Credentials | None:
    credentials = load_credentials(project_root, user_id, scopes)
    if not credentials:
        return None

    if credentials.valid:
        return credentials

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        if not os.getenv(TOKEN_ENV):
            save_credentials(project_root, user_id, credentials)
        return credentials

    return None


def has_credentials(project_root: Path, user_id: str, scopes: list[str]) -> bool:
    credentials = get_valid_credentials(project_root, user_id, scopes)
    return bool(credentials and credentials.valid)
