"""
TTS Provider — ElevenLabs Text-to-Speech
Returns raw MP3 audio bytes for a given text string.
"""

import os
import httpx


async def synthesize_speech(
    text: str,
    voice_id: str | None = None,
    settings_override: dict | None = None,
) -> bytes:
    """
    Convert text to speech using ElevenLabs.

    Args:
        text:              the text to speak
        voice_id:          ElevenLabs voice ID
        settings_override: dict from voice.json synthesis_settings

    Returns:
        MP3 audio bytes
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY is not set in environment")

    voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    # Merge defaults with any overrides from voice.json
    defaults = {
        "stability":         0.5,
        "similarity_boost":  0.75,
        "style":             0.2,
        "use_speaker_boost": True,
    }
    if settings_override:
        defaults.update({
            k: v for k, v in settings_override.items()
            if k in defaults
        })

    model_id = (settings_override or {}).get("model", "eleven_turbo_v2")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key":   api_key,
                "content-type": "application/json",
                "accept":       "audio/mpeg",
            },
            json={
                "text":           text,
                "model_id":       model_id,
                "voice_settings": defaults,
            },
        )

    if resp.status_code != 200:
        raise ValueError(f"ElevenLabs error {resp.status_code}: {resp.text}")

    return resp.content
