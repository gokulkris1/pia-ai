"""
PIA Backend — FastAPI Server
Handles: STT, LLM chat, TTS, serving frontend
Run: uvicorn main:app --reload --port 8000
"""

import os
import uuid
import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
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
from providers.tts import synthesize_speech, clone_voice_elevenlabs
from users.loader import load_user_profile, list_users
from persona.prompt_builder import build_system_prompt
from avatar.config import get_avatar_config
from memory.manager import MemoryManager
from session.call import CallSession

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
    image_base64: str | None = None   # optional JPEG frame from back camera (vision context)

class ChatResponse(BaseModel):
    session_id: str
    reply: str

class SpeakRequest(BaseModel):
    text: str
    voice_id: str | None = None

class StartCallResponse(BaseModel):
    session_id: str
    greeting: str
    persona_name: str

class OnboardProfile(BaseModel):
    name: str
    tagline: str = ""
    tone: str = "warm-but-direct"
    humor: str = "dry, understated"
    response_length: str = "2-4 sentences maximum"


# ── Onboarding routes ────────────────────────────────────────────────────────

@app.get("/api/onboard/status")
async def onboard_status():
    """Check if the user has completed onboarding."""
    persona_path = PROJECT_ROOT / "users" / DEFAULT_USER_ID / "persona.json"
    if persona_path.exists():
        data = json.loads(persona_path.read_text())
        return {"onboarded": data.get("onboarded", False), "name": data.get("display_name", "")}
    return {"onboarded": False, "name": ""}


@app.post("/api/onboard/profile")
async def save_onboard_profile(data: OnboardProfile):
    """Write user profile from onboarding wizard to persona.json."""
    user_dir = PROJECT_ROOT / "users" / DEFAULT_USER_ID
    user_dir.mkdir(parents=True, exist_ok=True)
    persona_path = user_dir / "persona.json"

    # Load existing as base (keep all the AI rules/defaults)
    existing = {}
    if persona_path.exists():
        existing = json.loads(persona_path.read_text())

    # Patch with onboarding data
    existing["onboarded"]    = True
    existing["display_name"] = data.name
    existing["twin_name"]    = "Pia"
    existing["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    existing["greeting"]     = f"Hey, I'm Pia \u2014 {data.name}'s AI twin. You can call me Pia, or rename me to whatever you'd like in settings. How's your day going? Anything on your mind?"

    if "identity" not in existing:
        existing["identity"] = {}
    existing["identity"]["background"] = data.tagline

    if "speaking_style" not in existing:
        existing["speaking_style"] = {}
    existing["speaking_style"]["tone"]                      = data.tone
    existing["speaking_style"]["preferred_response_length"] = data.response_length

    if "humor" not in existing:
        existing["humor"] = {}
    existing["humor"]["style"] = data.humor

    persona_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))

    # Hot-reload global profile so next call uses new persona immediately
    global USER_PROFILE, PERSONA
    USER_PROFILE = load_user_profile(DEFAULT_USER_ID)
    PERSONA      = USER_PROFILE.persona

    print(f"[onboard] Profile saved for '{data.name}'")
    return {"status": "saved", "name": data.name}


@app.post("/api/onboard/voice-sample")
async def save_voice_sample(file: UploadFile = File(...)):
    """Store and clone the user's voice via ElevenLabs."""
    user_dir = PROJECT_ROOT / "users" / DEFAULT_USER_ID
    user_dir.mkdir(parents=True, exist_ok=True)

    content   = await file.read()
    mime_type = file.content_type or "audio/webm"

    # Persist the raw sample
    ext       = mime_type.split("/")[-1].split(";")[0] or "webm"
    out_path  = user_dir / f"voice_sample.{ext}"
    out_path.write_bytes(content)
    print(f"[onboard] Voice sample saved ({len(content):,} bytes, {mime_type})")

    # Try to clone via ElevenLabs
    profile    = load_user_profile(DEFAULT_USER_ID)
    voice_name = f"{profile.display_name}'s Pia"
    voice_id   = await clone_voice_elevenlabs(content, voice_name, mime_type)

    if voice_id:
        # Update voice.json so future TTS calls use the cloned voice
        voice_path = user_dir / "voice.json"
        try:
            voice_data = json.loads(voice_path.read_text()) if voice_path.exists() else {}
        except Exception:
            voice_data = {}

        voice_data.setdefault("active_voice", {})
        voice_data["active_voice"]["voice_id"]   = voice_id
        voice_data["active_voice"]["voice_name"]  = voice_name
        voice_data["active_voice"]["is_cloned"]   = True
        voice_data["active_voice"]["cloned_at"]   = datetime.utcnow().isoformat()
        voice_path.write_text(json.dumps(voice_data, indent=2))
        print(f"[onboard] voice.json updated with cloned voice_id={voice_id}")
        return {"status": "cloned", "voice_id": voice_id, "bytes": len(content)}

    return {"status": "saved", "voice_id": None, "bytes": len(content)}


@app.post("/api/onboard/photo")
async def save_onboard_photo(file: UploadFile = File(...)):
    """Save user photo as frontend avatar (served as /static/avatar.jpg)."""
    content = await file.read()
    # Serve from frontend/ so it's picked up by StaticFiles
    avatar_path = FRONTEND_DIR / "avatar.jpg"
    avatar_path.write_bytes(content)
    # Also keep a backup in the user folder
    user_dir = PROJECT_ROOT / "users" / DEFAULT_USER_ID
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "avatar_original.jpg").write_bytes(content)
    print(f"[onboard] Photo saved ({len(content):,} bytes)")
    return {"status": "saved"}


@app.get("/onboard")
async def serve_onboard():
    """Serve the onboarding wizard page."""
    return FileResponse(str(FRONTEND_DIR / "onboard.html"))


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


@app.get("/api/avatar/config")
async def avatar_config():
    """Return avatar animation config for the active user — consumed by frontend."""
    # Re-read profile so changes to avatar.json are picked up without restart
    profile = load_user_profile(DEFAULT_USER_ID)
    return get_avatar_config(profile.avatar)


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

    reply = await generate_response(
        user_message=req.user_message,
        persona=profile.persona,
        memory=session.memory,
        system_prompt_override=system_prompt,
        image_base64=req.image_base64,
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

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        fp = FRONTEND_DIR / path
        return FileResponse(str(fp)) if fp.exists() else FileResponse(str(FRONTEND_DIR / "index.html"))
