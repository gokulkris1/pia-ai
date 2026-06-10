# Pia

Pia is a voice-first personal AI chief-of-staff for the founder as user zero.

## Milestone 1

Build only the spine:

```text
tap orb -> speech-to-text -> Claude -> calendar intent -> Google Calendar read/write
(ask-first for writes) -> text-to-speech -> orb animates while speaking
```

No second agent, no model router, no autonomous mode, and no avatar.

## Stack

- Frontend: vanilla JS static app in `frontend/`, hosted on Firebase Hosting.
- Backend: existing FastAPI app in `backend/`, containerized for Cloud Run.
- STT/TTS: Whisper/OpenAI transcription fallback and ElevenLabs speech.
- LLM: Claude for M1 (`LLM_ENGINE=claude`).

Read `docs/README.md` first; the full build order and constraints live in `docs/`.
