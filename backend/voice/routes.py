"""Realtime voice (Vapi) HTTP routes.

Three endpoints:
  * POST /api/voice/llm/chat/completions  — OpenAI-compatible custom-LLM (auth-gated)
  * POST /api/voice/tools/calendar        — Vapi server-tool webhook (auth-gated)
  * GET  /api/voice/config                — non-secret client config (public)

The two POST endpoints are called server-to-server by Vapi and are gated by
``require_vapi_auth`` — the calendar one can WRITE the calendar, so it is never
publicly callable. ``/api/voice/config`` returns only non-secret selection
(public key, provider/voice names from env) and is safe for the browser.
"""

from __future__ import annotations

import json
import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from voice.auth import require_vapi_auth
from voice.llm_shim import extract_messages_and_tools, stream_openai_chunks
from voice import sessions as voice_sessions
from voice import tools as voice_tools

router = APIRouter(prefix="/api/voice", tags=["voice"])

# ── Voice selection ───────────────────────────────────────────────────────────
# Default = Hope (warm, natural, female). The founder can swap it permanently via
# the ELEVENLABS_VOICE_ID env var. DEV_VOICES is a hardcoded audition shortlist
# for picking the final voice live in the real pipeline — it is NOT a user
# setting and is never persisted per-user. The config endpoint only honours a
# ?voiceId= override if it is one of these (or the env default), so the public
# endpoint can't be used to point Pia at an arbitrary paid voice.
HOPE_VOICE_ID = "zGjIP4SZlMnY9m93k97r"
DEV_VOICES = [
    {"id": "zGjIP4SZlMnY9m93k97r", "label": "Hope (default)"},
    {"id": "EQx6HGDYjkDpcli6vorJ", "label": "Voice 2"},
    {"id": "0WKkG7JmcKK7MkwhnMIe", "label": "Voice 3"},
    {"id": "6fZce9LFNG3iEITDfqZZ", "label": "Voice 4"},
]


def _default_voice_id() -> str:
    return os.getenv("ELEVENLABS_VOICE_ID", HOPE_VOICE_ID)


def _allowed_voice_ids() -> set[str]:
    return {_default_voice_id(), *(v["id"] for v in DEV_VOICES)}


def _resolve_voice_id(requested: str | None) -> str:
    """Use the dev-switcher override only if it's in the hardcoded allow-list."""
    if requested and requested in _allowed_voice_ids():
        return requested
    return _default_voice_id()


def _voice_stability() -> float:
    try:
        return float(os.getenv("ELEVENLABS_STABILITY", "0.45"))
    except ValueError:
        return 0.45


def _voice_similarity() -> float:
    try:
        return float(os.getenv("ELEVENLABS_SIMILARITY", "0.9"))
    except ValueError:
        return 0.9

# ── Cost guardrail ──────────────────────────────────────────────────────────
# A left-open session must not run unbounded. We cap call duration (enforced by
# Vapi via maxDurationSeconds in the client config, and surfaced to the client
# so it can auto-end), and we log per-call age + active-session count so spend
# is visible while testing.
DEFAULT_MAX_SESSION_SECONDS = 600  # 10 minutes


def _max_session_seconds() -> int:
    try:
        return max(30, int(os.getenv("VAPI_MAX_SESSION_SECONDS", DEFAULT_MAX_SESSION_SECONDS)))
    except ValueError:
        return DEFAULT_MAX_SESSION_SECONDS


def _user_id() -> str:
    return os.getenv("PIA_USER_ID", "default")


def _log_cost_visibility(call_id: str, label: str) -> None:
    sess = voice_sessions.get_or_create(call_id) if call_id else None
    age = f"{sess.age_seconds():.0f}s" if sess else "n/a"
    print(
        f"[voice-cost] {label} call={call_id or 'unknown'} age={age} "
        f"cap={_max_session_seconds()}s active_sessions={voice_sessions.active_count()}"
    )


def _extract_call_id(body: dict) -> str:
    """Find the Vapi call id wherever it is nested in the payload."""
    for container in (body, body.get("message") or {}, body.get("call") or {}):
        if isinstance(container, dict):
            call = container.get("call")
            if isinstance(call, dict) and call.get("id"):
                return str(call["id"])
            if container.get("callId"):
                return str(container["callId"])
    return ""


@router.post("/llm/chat/completions", dependencies=[Depends(require_vapi_auth)])
async def voice_llm(request: Request):
    """Custom-LLM endpoint Vapi streams from. Brain stays Claude via our shim."""
    body = await request.json()
    messages, tools = extract_messages_and_tools(body)

    # Vapi configures the calendar tools on the assistant; if it doesn't pass
    # them through, advertise ours so the model can still call them.
    if not tools:
        tools = voice_tools.TOOL_DEFINITIONS

    call_id = _extract_call_id(body)
    _log_cost_visibility(call_id, "llm")

    return StreamingResponse(
        stream_openai_chunks(messages, tools, _user_id()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/tools/calendar", dependencies=[Depends(require_vapi_auth)])
async def voice_calendar_tool(request: Request):
    """Vapi server-tool webhook. Routes every tool call through the ask-first gate."""
    body = await request.json()
    message = body.get("message") if isinstance(body.get("message"), dict) else body
    call_id = _extract_call_id(body)
    _log_cost_visibility(call_id, "tool")

    tool_calls = message.get("toolCalls") or message.get("tool_calls") or []
    results = []
    for tc in tool_calls:
        fn = tc.get("function", {})
        name = fn.get("name")
        raw_args = fn.get("arguments")
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args) if raw_args.strip() else {}
            except json.JSONDecodeError:
                args = {}
        else:
            args = raw_args or {}

        try:
            result_text = voice_tools.dispatch(call_id or "default", name, args)
        except Exception as err:  # noqa: BLE001 — never crash the live call
            print(f"[voice-tool] dispatch error for {name}: {err}")
            result_text = "Sorry — I couldn't reach your calendar just then."

        results.append({"toolCallId": tc.get("id"), "result": result_text})

    return JSONResponse({"results": results})


@router.get("/config")
async def voice_config(request: Request):
    """Non-secret client config for the Vapi Web SDK.

    Lets the founder audition/swap the ElevenLabs voice + model and STT model via
    env vars (no code change) — secrets (provider API keys, webhook secret) stay
    on the server / in Vapi. An optional ?voiceId= picks one of the hardcoded
    DEV_VOICES for live auditioning; anything else falls back to the default.
    """
    max_seconds = _max_session_seconds()
    voice_id = _resolve_voice_id(request.query_params.get("voiceId"))
    eleven_model = os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2_5")
    deepgram_model = os.getenv("DEEPGRAM_MODEL", "nova-2")

    return {
        # 'classic' keeps the existing request/response loop; 'vapi' uses WebRTC.
        "voiceMode": os.getenv("PIA_VOICE_MODE", "classic"),
        "publicKey": os.getenv("VAPI_PUBLIC_KEY", ""),
        "assistantId": os.getenv("VAPI_ASSISTANT_ID", ""),
        "maxSessionSeconds": max_seconds,
        # Dev-only audition shortlist + current selection (not a user setting).
        "devVoices": DEV_VOICES,
        "voiceId": voice_id,
        # Applied as assistantOverrides so voice/STT are env-swappable at runtime.
        "assistantOverrides": {
            "maxDurationSeconds": max_seconds,
            "transcriber": {
                "provider": "deepgram",
                "model": deepgram_model,
                "language": "en",
            },
            "voice": {
                "provider": "11labs",
                "voiceId": voice_id,
                "model": eleven_model,
                "stability": _voice_stability(),
                "similarityBoost": _voice_similarity(),
            },
        },
    }
