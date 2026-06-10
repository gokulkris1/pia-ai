from __future__ import annotations

import json
import os
from pathlib import Path

import google.auth
from google.auth.transport.requests import Request
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials

TOKEN_ENV = "GOOGLE_CALENDAR_TOKEN_JSON"
TOKEN_PATH_ENV = "GOOGLE_CALENDAR_TOKEN_PATH"
TOKEN_SECRET_ENV = "GOOGLE_CALENDAR_TOKEN_SECRET"
PROJECT_ENV = "GOOGLE_CLOUD_PROJECT"


def token_path(project_root: Path, user_id: str) -> Path:
    configured = os.getenv(TOKEN_PATH_ENV)
    if configured:
        return Path(configured).expanduser()
    return project_root / "users" / user_id / "google_calendar_token.json"


def load_credentials(project_root: Path, user_id: str, scopes: list[str]) -> Credentials | None:
    token_json = os.getenv(TOKEN_ENV)
    if token_json:
        try:
            token_info = json.loads(token_json)
            if _has_required_scopes(token_info, scopes):
                return Credentials.from_authorized_user_info(token_info, scopes=scopes)
            print(f"[calendar] {TOKEN_ENV} does not include the required scopes; checking token file")
        except Exception as err:
            print(f"[calendar] Failed to load {TOKEN_ENV}: {err}")

    path = token_path(project_root, user_id)
    if not path.exists():
        return None

    try:
        token_info = json.loads(path.read_text(encoding="utf-8"))
        if not _has_required_scopes(token_info, scopes):
            return None
        return Credentials.from_authorized_user_info(token_info, scopes=scopes)
    except Exception as err:
        print(f"[calendar] Failed to load token file {path}: {err}")
        return None


def save_credentials(project_root: Path, user_id: str, credentials: Credentials) -> Path:
    path = token_path(project_root, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    token_json = credentials.to_json()
    path.write_text(token_json, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    _save_credentials_secret(token_json)
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


def _has_required_scopes(token_info: dict, required_scopes: list[str]) -> bool:
    granted = set(token_info.get("scopes") or [])
    if not granted:
        return True
    return set(required_scopes).issubset(granted)


def _save_credentials_secret(token_json: str) -> None:
    secret_id = os.getenv(TOKEN_SECRET_ENV)
    project_id = os.getenv(PROJECT_ENV)
    if not secret_id or not project_id:
        return

    try:
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        session = AuthorizedSession(credentials)
        response = session.post(
            f"https://secretmanager.googleapis.com/v1/projects/{project_id}/secrets/{secret_id}:addVersion",
            json={"payload": {"data": _base64(token_json)}},
            timeout=10,
        )
        if response.status_code >= 300:
            print(f"[calendar] Failed to persist token secret: {response.status_code} {response.text}")
    except Exception as err:
        print(f"[calendar] Failed to persist token secret: {err}")


def _base64(value: str) -> str:
    import base64

    return base64.b64encode(value.encode("utf-8")).decode("ascii")
