"""Realtime voice (Vapi) integration package.

Houses the auth gate, the OpenAI-compatible LLM shim, the calendar tool
webhook, and the lightweight per-call session store used by the realtime
voice path. The classic request/response loop in ``main.py`` is unaffected
and remains the runtime fallback (``PIA_VOICE_MODE='classic'``).
"""
