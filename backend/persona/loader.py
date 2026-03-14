"""
Persona Loader — now reads from users/<user_id>/persona.json via UserProfile.
Kept for backward compatibility; main.py uses load_user_profile() directly.
"""

from typing import Any


def load_persona(user_id: str = "default") -> dict[str, Any]:
    """
    Load persona for a given user.
    Delegates to the UserProfile system so there is one source of truth.
    """
    from users.loader import load_user_profile   # local import avoids circular
    profile = load_user_profile(user_id)
    return profile.persona
