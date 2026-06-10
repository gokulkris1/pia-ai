"""
PIA Backend — FastAPI Server
Handles: STT, LLM chat, TTS, serving frontend
Run: uvicorn main:app --reload --port 8000
"""

import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# ── Paths ─────────────────────────────────────────────────────────────────────
BACKEND_DIR  = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

from providers.stt import transcribe_audio
from providers.llm import generate_response
from providers.tts import synthesize_speech
from users.loader import load_user_profile, list_users
from persona.prompt_builder import build_system_prompt
from memory.manager import MemoryManager
from session.call import CallSession
from calendar_agent.google_client import (
    CalendarNotConnectedError,
    exchange_code,
    format_events_for_voice,
    get_authorization_url,
    read_events,
)
from calendar_agent.intent import get_time_window, is_calendar_read_intent
from calendar_agent.store import has_credentials
from calendar_agent.google_client import SCOPES

app = FastAPI(title="PIA Backend", version="1.0.0")

# CORS — allow all for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global state ──────────────────────────────────────────────────────────────
sessions: dict[str, CallSession] = {}

# Load default user profile at startup (hot-reloaded per-request for training)
DEFAULT_USER_ID = os.getenv("PIA_USER_ID", "default")
USER_PROFILE = load_user_profile(DEFAULT_USER_ID)

# Keep backward-compat alias used by legacy code paths
PERSONA = USER_PROFILE.persona


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    user_message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str

class SpeakRequest(BaseModel):
    text: str
    voice_id: str | None = None


class CalendarStatusResponse(BaseModel):
    connected: bool
    auth_url: str


class CalendarReadResponse(BaseModel):
    connected: bool
    label: str
    events: list[dict]
    reply: str


class StartCallResponse(BaseModel):
    session_id: str
    greeting: str
    persona_name: str


# ── API routes ────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status":   "ok",
        "twin":     USER_PROFILE.twin_name,
        "user":     USER_PROFILE.display_name,
        "user_id":  USER_PROFILE.user_id,
    }


@app.get("/api/users")
async def get_users():
    """List all configured user profiles."""
    return {"users": list_users(), "active": DEFAULT_USER_ID}


@app.get("/api/calendar/auth")
async def calendar_auth():
    """Start Google Calendar OAuth."""
    try:
        return RedirectResponse(get_authorization_url())
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err)) from err


@app.get("/api/calendar/callback")
async def calendar_callback(code: str | None = None, error: str | None = None):
    """Google OAuth callback: store the founder's calendar token."""
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth failed: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing Google OAuth code")

    try:
        exchange_code(PROJECT_ROOT, DEFAULT_USER_ID, code)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err)) from err

    return HTMLResponse(
        "<html><body><h1>Calendar connected</h1>"
        "<p>Pia can now read your calendar. You can close this tab.</p></body></html>"
    )


@app.get("/api/calendar/status", response_model=CalendarStatusResponse)
async def calendar_status():
    """Return whether Google Calendar is connected for the active founder profile."""
    return CalendarStatusResponse(
        connected=has_credentials(PROJECT_ROOT, DEFAULT_USER_ID, SCOPES),
        auth_url="/api/calendar/auth",
    )


@app.get("/api/calendar/read", response_model=CalendarReadResponse)
async def calendar_read(q: str = Query("what's on my calendar tomorrow")):
    """Read calendar events for a narrow natural-language time window."""
    timezone_name = os.getenv("PIA_TIMEZONE", "Europe/Dublin")
    start, end, label = get_time_window(q, timezone_name)

    try:
        events = read_events(PROJECT_ROOT, DEFAULT_USER_ID, start, end)
    except CalendarNotConnectedError:
        return CalendarReadResponse(
            connected=False,
            label=label,
            events=[],
            reply="Calendar is not connected yet. Open /api/calendar/auth first, then ask me again.",
        )

    return CalendarReadResponse(
        connected=True,
        label=label,
        events=events,
        reply=format_events_for_voice(events, label),
    )


@app.post("/api/call/start", response_model=StartCallResponse)
async def start_call():
    """Begin a new call session. Returns session ID and Pia's opening line."""
    # Re-read profile on each call so persona edits are reflected immediately
    profile  = load_user_profile(DEFAULT_USER_ID)
    persona  = profile.persona

    session_id = str(uuid.uuid4())
    session = CallSession(session_id=session_id, persona=persona)
    sessions[session_id] = session

    # Generate a fresh, natural greeting via LLM so it varies and sounds human
    try:
        hour = datetime.now().hour
        if hour < 12:    time_of_day = "morning"
        elif hour < 17:  time_of_day = "afternoon"
        else:            time_of_day = "evening"

        name = persona.get("display_name", "")
        base_prompt = build_system_prompt(persona)
        greeting_prompt = (
            base_prompt
            + f"\n\nGREETING MODE: This is the very first thing you say on a call. "
            + "Your name is Pia — always say it as one word like a name, never spell it out as letters. "
            + f"It\'s {time_of_day}. "
            + "Do ALL of the following in 3–4 natural spoken sentences:\n"
            + "1. Introduce yourself as Pia, the AI twin.\n"
            + "2. Casually mention they can rename you to anything they want in settings.\n"
            + "3. Open a warm, genuine conversation — ask how their day\'s going, what\'s on their mind, "
            + "comment on the time of day or make a light casual remark about the weather or plans for the day.\n"
            + "Sound like a real person, not an assistant. No filler words like \'certainly\' or \'absolutely\'. No lists."
        )
        greeting = await generate_response(
            user_message="[call started]",
            persona=persona,
            memory=MemoryManager(),
            system_prompt_override=greeting_prompt,
        )
    except Exception as e:
        print(f"[start_call] LLM greeting failed ({e}) — using fallback")
        greeting = persona.get(
            "greeting",
            "Hey, I'm Pia — your AI twin. You can rename me whatever you like in settings. How's your day going?",
        )

    return StartCallResponse(
        session_id=session_id,
        greeting=greeting,
        persona_name=profile.twin_name,
    )


@app.post("/api/call/end/{session_id}")
async def end_call(session_id: str):
    """Terminate a call session and free its memory."""
    session = sessions.pop(session_id, None)
    duration = session.duration_str() if session else "0:00"
    return {"status": "ended", "duration": duration}


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """
    Accept an audio blob (webm/wav/mp4) and return a text transcript.
    Uses OpenAI Whisper API.
    """
    audio_bytes = await file.read()
    text = await transcribe_audio(audio_bytes, file.filename or "audio.webm")
    return {"transcript": text}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Send a user message and get PIA's persona-aware reply.
    Maintains rolling conversation memory per session.
    """
    session = sessions.get(req.session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found. Call /api/call/start first.",
        )

    # Re-read persona so live edits to persona.json take effect without restart
    profile       = load_user_profile(DEFAULT_USER_ID)
    system_prompt = build_system_prompt(profile.persona, mode="call")

    if is_calendar_read_intent(req.user_message):
        timezone_name = os.getenv("PIA_TIMEZONE", "Europe/Dublin")
        start, end, label = get_time_window(req.user_message, timezone_name)
        try:
            events = read_events(PROJECT_ROOT, DEFAULT_USER_ID, start, end)
            reply = format_events_for_voice(events, label)
        except CalendarNotConnectedError:
            reply = "Calendar is not connected yet. Open the calendar connect link at /api/calendar/auth, then ask me again."

        session.memory.add("user", req.user_message)
        session.memory.add("assistant", reply)
        session.record_turn()
        return ChatResponse(session_id=req.session_id, reply=reply)

    reply = await generate_response(
        user_message=req.user_message,
        persona=profile.persona,
        memory=session.memory,
        system_prompt_override=system_prompt,
    )

    # Persist to memory
    session.memory.add("user", req.user_message)
    session.memory.add("assistant", reply)
    session.record_turn()

    return ChatResponse(session_id=req.session_id, reply=reply)


@app.post("/api/speak")
async def speak(req: SpeakRequest):
    """
    Convert text to speech using ElevenLabs.
    Voice ID resolved from: request body → voice.json → env var → hardcoded default.
    Returns raw MP3 audio bytes.
    """
    profile  = load_user_profile(DEFAULT_USER_ID)
    voice_id = (
        req.voice_id
        or profile.active_voice_id
        or os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    )
    tts_settings = profile.voice.get("synthesis_settings", {})

    audio_bytes = await synthesize_speech(
        text=req.text,
        voice_id=voice_id,
        settings_override=tts_settings,
    )
    return Response(content=audio_bytes, media_type="audio/mpeg")


# ── Serve frontend ────────────────────────────────────────────────────────────

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def root():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def api_not_found(path: str):
        raise HTTPException(status_code=404, detail=f"API route not found: /api/{path}")

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        fp = FRONTEND_DIR / path
        return FileResponse(str(fp)) if fp.exists() else FileResponse(str(FRONTEND_DIR / "index.html"))
