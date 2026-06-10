"""
User Profile Loader — loads the founder profile for Pia.
Combines persona.json and voice.json into a single UserProfile.

Usage:
    from users.loader import load_user_profile
    profile = load_user_profile("default")
    profile.persona    # dict from persona.json
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

    def __repr__(self) -> str:
        return f"UserProfile(id={self.user_id!r}, persona={self.twin_name!r})"


def load_user_profile(user_id: str = "default") -> UserProfile:
    """
    Load a user's complete Pia profile from users/<user_id>/.

    Args:
        user_id: folder name under users/  (default: "default")

    Returns:
        UserProfile with .persona and .voice populated.
        Falls back to safe defaults if any file is missing.
    """
    user_dir = USERS_DIR / user_id

    if not user_dir.exists():
        print(f"[users] No directory for user '{user_id}' — using defaults")
        return _default_profile(user_id)

    persona = _load_json(user_dir / "persona.json", _default_persona())
    voice   = _load_json(user_dir / "voice.json",   _default_voice())

    profile = UserProfile(user_id=user_id, persona=persona, voice=voice, _root=user_dir)
    print(f"[users] Loaded profile for '{profile.display_name}' (persona: {profile.twin_name})")
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
        voice=_default_voice(),
    )


def _default_persona() -> dict:
    return {
        "display_name": "User",
        "twin_name":    "PIA",
        "greeting":     "Hey, I'm Pia \u2014 your Chief of Staff for calendar, agents, and digital life. What should we sort out first?",
        "speaking_style": {"preferred_response_length": "2\u20134 sentences"},
        "rules": [
            "Keep responses to 2\u20134 short sentences",
            "Never use markdown, lists, or headers",
            "Sound natural, warm, and conversational",
            "Never break character",
            "Never claim to be the user, speak as the user, or impersonate anyone",
            "Never say 'Certainly', 'Absolutely', 'Great question' or any hollow affirmation",
            "Be opinionated — take real positions, don't hedge everything",
        ],
        "typical_phrases": [],
        "dislikes_in_ai_responses": ["Certainly!", "Great question!"],
    }


def _default_voice() -> dict:
    return {
        "provider": "elevenlabs",
        "active_voice": {"voice_id": "21m00Tcm4TlvDq8ikWAM"},
        "synthesis_settings": {
            "model":            "eleven_turbo_v2_5",  # faster + more expressive than v2
            "stability":         0.33,                # lower = more natural variation
            "similarity_boost":  0.88,                # higher = closer to cloned voice
            "style":             0.45,                # more character and emotion
            "use_speaker_boost": True,
        },
    }
