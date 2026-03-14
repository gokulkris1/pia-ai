"""
Avatar Config Loader — exposes avatar.json settings to the backend
and builds the avatar config payload sent to the frontend.

The frontend avatar.js reads window.__AVATAR_CONFIG__ which is injected
at page load via the /api/avatar/config endpoint.

Usage:
    from avatar.config import get_avatar_config
    config = get_avatar_config(avatar_profile)
"""

from typing import Any


def get_avatar_config(avatar_profile: dict[str, Any]) -> dict[str, Any]:
    """
    Distill avatar.json into a clean config dict for the frontend.

    Returns only the fields the frontend actually needs,
    keeping future/internal fields server-side.
    """
    source = avatar_profile.get("source", {})
    display = avatar_profile.get("display", {})
    idle = avatar_profile.get("idle_animation", {})
    speaking = avatar_profile.get("speaking_animation", {})

    return {
        # Photo source — frontend will request /static/<file>
        "photo_file": source.get("file", "avatar.jpg"),
        "photo_type": source.get("type", "photo"),

        # Display
        "shape":           display.get("shape", "circle"),
        "size_desktop":    display.get("size_desktop", 200),
        "size_mobile":     display.get("size_mobile", 160),
        "object_position": display.get("object_position", "center top"),

        # Idle animation
        "idle_enabled":    idle.get("enabled", True),
        "idle_mode":       idle.get("mode", "breathe"),
        "idle_scale_min":  idle.get("scale_min", 1.0),
        "idle_scale_max":  idle.get("scale_max", 1.012),
        "idle_duration":   idle.get("duration_seconds", 4),

        # Speaking animation
        "speaking_enabled":    speaking.get("enabled", True),
        "speaking_mode":       speaking.get("mode", "audio_reactive"),
        "mouth_overlay":       speaking.get("mouth_overlay", True),
        "mouth_min_height":    speaking.get("mouth_min_height_px", 2),
        "mouth_max_height":    speaking.get("mouth_max_height_px", 28),
        "smoothing":           speaking.get("smoothing", 0.75),
        "amplitude_threshold": speaking.get("amplitude_threshold", 8),
        "ripple_rings":        speaking.get("ripple_rings", 3),
        "ring_color":          speaking.get("ring_color", "rgba(52, 199, 89, 0.35)"),

        # Future capability flags — all false in MVP
        "future": {
            "facial_expressions": False,
            "head_movement":      False,
            "lip_sync":           False,
            "body_language":      False,
        },

        # Training metadata
        "training_enabled": avatar_profile.get("training_metadata", {})
                                          .get("training_signals_enabled", False),
    }


def merge_avatar_overrides(base_config: dict, overrides: dict) -> dict:
    """
    Apply runtime overrides to an avatar config.
    Useful for future per-session avatar adjustments.
    """
    merged = {**base_config}
    merged.update(overrides)
    return merged
