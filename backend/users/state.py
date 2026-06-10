from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from users.loader import USERS_DIR

STATE_FILE_NAME = "pia_state.json"


def _state_path(user_id: str) -> Path:
    return USERS_DIR / user_id / STATE_FILE_NAME


def load_user_state(user_id: str) -> dict[str, Any]:
    path = _state_path(user_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_user_state(user_id: str, state: dict[str, Any]) -> None:
    path = _state_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def has_been_introduced(user_id: str) -> bool:
    return bool(load_user_state(user_id).get("has_been_introduced"))


def mark_introduced(user_id: str) -> None:
    state = load_user_state(user_id)
    state["has_been_introduced"] = True
    save_user_state(user_id, state)
