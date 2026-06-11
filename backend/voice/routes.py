"""Realtime voice (Vapi) HTTP routes.

All routes here are called server-to-server by Vapi and are gated by
``require_vapi_auth`` — except ``/api/voice/config``, which returns only
non-secret client selection (public key, provider/voice names) and is safe
to call from the browser.

NOTE: handlers below are intentionally minimal in this first commit. Auth is
built and proven (unsigned -> 401) BEFORE the calendar tool is wired, per the
security requirement that the calendar-writing endpoint never be public.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from voice.auth import require_vapi_auth

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/llm/chat/completions", dependencies=[Depends(require_vapi_auth)])
async def voice_llm(request: Request):
    """OpenAI-compatible custom-LLM endpoint Vapi streams from. (stub — wired next)"""
    return {"ok": True, "stub": "llm"}


@router.post("/tools/calendar", dependencies=[Depends(require_vapi_auth)])
async def voice_calendar_tool(request: Request):
    """Vapi server-tool webhook for ask-first calendar actions. (stub — wired after auth proven)"""
    return {"ok": True, "stub": "calendar"}
