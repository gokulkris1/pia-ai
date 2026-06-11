"""Lightweight per-call state for the realtime voice path.

Vapi is stateless toward us across tool calls within a single voice call, but
the ask-first gate needs to remember a pending proposal between the
``propose_event`` and ``confirm_event`` tool calls. We key that state by the
Vapi ``call.id`` (provided on every server message).

This store is intentionally tiny and in-memory — the brain and calendar logic
live elsewhere. It also tracks ``started_at`` so we have spend/duration
visibility while testing (see the cost guardrail in ``routes.py``).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VoiceSession:
    """Per-Vapi-call state. Satisfies the ``HasPendingAction`` protocol."""

    call_id: str
    started_at: float = field(default_factory=time.monotonic)
    pending_calendar_action: dict[str, Any] | None = None

    def age_seconds(self) -> float:
        return time.monotonic() - self.started_at


_SESSIONS: dict[str, VoiceSession] = {}


def get_or_create(call_id: str) -> VoiceSession:
    sess = _SESSIONS.get(call_id)
    if sess is None:
        sess = VoiceSession(call_id=call_id)
        _SESSIONS[call_id] = sess
    return sess


def drop(call_id: str) -> None:
    _SESSIONS.pop(call_id, None)


def active_count() -> int:
    return len(_SESSIONS)
