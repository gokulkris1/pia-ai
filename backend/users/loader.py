"""
User Profile Loader — loads the full twin profile for a given user.
Combines persona.json, avatar.json, voice.json into a single UserProfile.

Usage:
    from users.loader import load_user_profile
    profile = load_user_profile("default")
    profile.persona    # dict from persona.json
    profile.avatar     # dict from avatar.json
    profile.voice      # dict from voice.json
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Root of the project (two levels up from backend/users/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
USERS_DIR    = PROJECT_ROOT / "users"


@dataclass
class UserProfile:
    user_id:  str
    persona:  dict[str, Any]
    avatar:   dict[str, Any]
    voice:    dict[str, Any]
    _root:    Path = field(repr=False, default=None)

    @property
    def display_name(self) -> str:
        return self.persona.get("display_name", self.user_id)

    @property
    def twin_name(self) -> str:
        return self.persona.get("twin_name", "PIA")

    @property
    def active_voice_id(self) -> str:
        return self.voice.get("active_voice", {}).get("voice_id", "21m00Tcm4TlvDq8ikWAM")

    @property
    def avatar_photo_path(self) -> Path | None:
        """Returns absolute path to the avatar photo, or None if not found."""
        photo = self.avatar.get("source", {}).get("file", "avatar.jpg")
        # Check frontend/ first (where the web server serves it from), then user dir
        candidates = [
            PROJECT_ROOT / "frontend" / photo,
            self._root / photo,
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    def __repr__(self) -> str:
        return f"UserProfile(id={self.user_id!r}, twin={self.twin_name!r})"


def load_user_profile(user_id: str = "default") -> UserProfile:
    """
    Load a user's complete twin profile from users/<user_id>/.

    Args:
        user_id: folder name under users/  (default: "default")

    Returns:
        UserProfile with .persona, .avatar, .voice populated.
        Falls back to safe defaults if any file is missing.
    """
    user_dir = USERS_DIR / user_id

    if not user_dir.exists():
        print(f"[users] No directory for user '{user_id}' — using defaults")
        return _default_profile(user_id)

    persona = _load_json(user_dir / "persona.json", _default_persona())
    avatar  = _load_json(user_dir / "avatar.json",  _default_avatar())
    voice   = _load_json(user_dir / "voice.json",   _default_voice())

    profile = UserProfile(user_id=user_id, persona=persona, avatar=avatar, voice=voice, _root=user_dir)
    print(f"[users] Loaded profile for '{profile.display_name}' (twin: {profile.twin_name})")
    return profile


def list_users() -> list[str]:
    """Return all available user IDs."""
    if not USERS_DIR.exists():
        return []
    return [d.name for d in USERS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        print(f"[users] {path.name} not found — using defaults")
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[users] Failed to parse {path}: {e}")
        return default


def _default_profile(user_id: str) -> UserProfile:
    return UserProfile(
        user_id=user_id,
        persona=_default_persona(),
        avatar=_default_avatar(),
        voice=_default_voice(),
    )


def _default_persona() -> dict:
    return {
        "display_name": "User",
        "twin_name":    "PIA",
        "greeting":     "Hey! PIA here — what's on your mind?",
        "speaking_style": {"preferred_response_length": "2–4 sentences"},
        "rules": [
            "Keep responses to 2–4 short sentences",
            "Never use markdown, lists, or headers",
            "Sound natural, like on a voice call",
            "Never break character",
        ],
        "typical_phrases": [],
        "dislikes_in_ai_responses": ["Certainly!", "Great question!"],
    }


def _default_avatar() -> dict:
    return {
        "source": {"type": "photo", "file": "avatar.jpg"},
        "idle_animation": {"enabled": True, "mode": "breathe"},
        "speaking_animation": {"enabled": True, "mode": "audio_reactive"},
    }


def _default_voice() -> dict:
    return {
        "provider": "elevenlabs",
        "active_voice": {"voice_id": "21m00Tcm4TlvDq8ikWAM"},
        "synthesis_settings": {
            "model":            "eleven_turbo_v2",
            "stability":         0.5,
            "similarity_boost":  0.75,
            "style":             0.2,
            "use_speaker_boost": True,
        },
    }
