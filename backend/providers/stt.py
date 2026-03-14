"""
STT Provider — Speech-to-Text via OpenAI Whisper API
Accepts raw audio bytes, returns transcript string.
"""

import os
import httpx


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """
    Transcribe audio using OpenAI Whisper API.

    Args:
        audio_bytes: raw audio data (webm, wav, mp4, mp3, m4a)
        filename:    original filename (used to hint content type)

    Returns:
        Transcribed text string
    """
    api_key = os.getenv("OpenAI_Key")
    if not api_key:
        raise ValueError("OpenAI_Key is not set in environment")

    # Detect MIME type from filename extension
    ext = filename.rsplit(".", 1)[-1].lower()
    mime_map = {
        "webm": "audio/webm",
        "wav":  "audio/wav",
        "mp4":  "audio/mp4",
        "mp3":  "audio/mpeg",
        "m4a":  "audio/m4a",
        "ogg":  "audio/ogg",
    }
    mime = mime_map.get(ext, "audio/webm")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={
                "file":     (filename, audio_bytes, mime),
                "model":    (None, "whisper-1"),
                "language": (None, "en"),
            },
        )

    if response.status_code != 200:
        raise ValueError(f"Whisper API error {response.status_code}: {response.text}")

    return response.json().get("text", "").strip()
