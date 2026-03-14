"""
TTS Provider — ElevenLabs (primary) → OpenAI TTS (automatic fallback)
Returns raw MP3 audio bytes for a given text string.
"""

import os
import re
import httpx


def _clean_for_tts(text: str) -> str:
    """
    Pre-process text before sending to TTS so it reads naturally.
    - 'PIA' as standalone word → 'Pia'  (avoids letter-by-letter reading)
    - Strip markdown bold/italic markers
    """
    # Replace all-caps 'PIA' (as a word) with 'Pia'
    text = re.sub(r'\bPIA\b', 'Pia', text)
    # Strip common markdown that slips through
    text = re.sub(r'[*_`#]', '', text)
    return text.strip()


async def synthesize_speech(
    text: str,
    voice_id: str | None = None,
    settings_override: dict | None = None,
) -> bytes:
    """
    Convert text to speech.
    Tries ElevenLabs first; on any failure falls back to OpenAI TTS.

    Args:
        text:              the text to speak
        voice_id:          ElevenLabs voice ID (ignored for OpenAI fallback)
        settings_override: dict from voice.json synthesis_settings

    Returns:
        MP3 audio bytes
    """
    text = _clean_for_tts(text)
    try:
        return await _call_elevenlabs(text, voice_id, settings_override)
    except Exception as el_err:
        print(f"[tts] ElevenLabs failed ({el_err}) — falling back to OpenAI TTS")
        return await _call_openai_tts(text)


# ── ElevenLabs ────────────────────────────────────────────────────────────────

async def _call_elevenlabs(
    text: str,
    voice_id: str | None = None,
    settings_override: dict | None = None,
) -> bytes:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY is not set")

    voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    defaults = {
        "stability":         0.33,   # lower = more expressive/varied
        "similarity_boost":  0.88,   # higher = truer to the cloned voice
        "style":             0.45,   # more character/emotion
        "use_speaker_boost": True,
    }
    if settings_override:
        defaults.update({k: v for k, v in settings_override.items() if k in defaults})

    model_id = (settings_override or {}).get("model", "eleven_turbo_v2_5")

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


# ── OpenAI TTS fallback ───────────────────────────────────────────────────────

async def _call_openai_tts(text: str) -> bytes:
    api_key = os.getenv("OpenAI_Key")
    if not api_key:
        raise ValueError("OpenAI_Key is not set — cannot use TTS fallback")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model": "tts-1-hd",   # hd = higher quality, less robotic
                "input": text,
                "voice": "onyx",       # onyx: warm, deep, natural; options: alloy echo fable onyx nova shimmer
            },
        )

    if resp.status_code != 200:
        raise ValueError(f"OpenAI TTS error {resp.status_code}: {resp.text}")

    return resp.content


# ── ElevenLabs Voice Cloning ─────────────────────────────────────────────────

async def clone_voice_elevenlabs(
    audio_bytes: bytes,
    voice_name: str,
    mime_type: str = "audio/webm",
) -> str | None:
    """
    Upload a voice sample to ElevenLabs and create a cloned voice.

    Args:
        audio_bytes: raw audio bytes (webm/ogg/mp4/wav)
        voice_name:  label for the cloned voice in ElevenLabs
        mime_type:   MIME type of the audio data

    Returns:
        voice_id string if successful, None on failure
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("[voice-clone] ELEVENLABS_API_KEY not set — skipping clone")
        return None

    # Choose a sensible file extension
    ext_map = {
        "audio/webm": "webm",
        "audio/ogg":  "ogg",
        "audio/mp4":  "m4a",
        "audio/wav":  "wav",
        "audio/mpeg": "mp3",
    }
    ext = ext_map.get(mime_type.split(";")[0].strip(), "webm")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.elevenlabs.io/v1/voices/add",
                headers={"xi-api-key": api_key},
                data={
                    "name":        voice_name,
                    "description": f"Cloned voice for {voice_name} AI twin",
                },
                files={
                    "files": (f"voice_sample.{ext}", audio_bytes, mime_type),
                },
            )

        if resp.status_code not in (200, 201):
            print(f"[voice-clone] ElevenLabs API error {resp.status_code}: {resp.text}")
            return None

        data = resp.json()
        voice_id = data.get("voice_id")
        print(f"[voice-clone] Created cloned voice '{voice_name}' → voice_id={voice_id}")
        return voice_id

    except Exception as e:
        print(f"[voice-clone] Failed: {e}")
        return None
