"""Shared ask-first calendar gate.

Single source of truth for the propose → confirm → execute flow, used by BOTH
the classic HTTP routes (``/api/calendar/*``, ``/api/chat``) and the realtime
voice tool webhook (``/api/voice/tools/calendar``).

Every function operates on a *session-like* object — anything exposing a
mutable ``pending_calendar_action`` attribute (``CallSession`` or the voice
``VoiceSession``). Reads never touch a session. Writes are NEVER executed here
without an explicit prior proposal + matching confirmation.
"""

from __future__ import annotations

import uuid
from typing import Any, Protocol

from calendar_agent.actions import (
    execute_calendar_action,
    is_confirmation,
    propose_calendar_write,
)
from calendar_agent.google_client import (
    CalendarNotConnectedError,
    format_events_for_voice,
    get_calendar_service,
    read_events,
)
from calendar_agent.intent import get_time_window

_NOT_CONNECTED_REPLY = (
    "Calendar needs access. Open /api/calendar/auth, approve access, then ask me again."
)


class HasPendingAction(Protocol):
    pending_calendar_action: dict[str, Any] | None


def assign_proposal_id(proposal: dict) -> dict:
    """Stamp a stable proposal id so confirmations can be matched to a proposal."""
    return {**proposal, "proposal_id": proposal.get("proposal_id") or str(uuid.uuid4())}


def read_calendar(project_root, user_id: str, query: str, timezone_name: str) -> dict:
    """Read events for a natural-language time window. Never writes."""
    start, end, label = get_time_window(query, timezone_name)
    try:
        events = read_events(project_root, user_id, start, end)
    except CalendarNotConnectedError:
        return {
            "connected": False,
            "label": label,
            "events": [],
            "reply": "Calendar is not connected yet. Open /api/calendar/auth, then ask me again.",
        }
    return {
        "connected": True,
        "label": label,
        "events": events,
        "reply": format_events_for_voice(events, label),
    }


def propose_change(
    project_root,
    user_id: str,
    session: HasPendingAction | None,
    text: str,
    timezone_name: str,
) -> dict:
    """Build a calendar write proposal and stash it on the session. Never writes."""
    try:
        proposal = propose_calendar_write(project_root, user_id, text, timezone_name)
    except CalendarNotConnectedError:
        return {"status": "not_connected", "reply": _NOT_CONNECTED_REPLY}

    if proposal.get("action") == "needs_detail":
        return {"status": "needs_detail", "reply": proposal["reply"]}

    proposal = assign_proposal_id(proposal)
    if session is not None:
        session.pending_calendar_action = proposal

    return {
        "status": "proposal",
        "reply": proposal["confirmation_prompt"],
        "proposal": proposal,
    }


def confirm_pending(
    project_root,
    user_id: str,
    session: HasPendingAction,
    confirmation: str,
    proposal_id: str | None = None,
) -> dict:
    """Execute the session's pending proposal — only on explicit confirmation."""
    pending = session.pending_calendar_action
    if not pending:
        return {
            "status": "no_pending_proposal",
            "reply": "I don't have a calendar change waiting for confirmation.",
        }

    # If a proposal id is supplied, it must match the one we're holding.
    if proposal_id is not None and proposal_id != pending.get("proposal_id"):
        return {
            "status": "proposal_mismatch",
            "reply": "That confirmation does not match the calendar change I'm holding.",
            "proposal": pending,
        }

    if not is_confirmation(confirmation):
        return {
            "status": "not_confirmed",
            "reply": "Say yes to confirm the calendar change, or no to leave it alone.",
            "proposal": pending,
        }

    try:
        service = get_calendar_service(project_root, user_id)
        reply = execute_calendar_action(service, pending)
        session.pending_calendar_action = None
    except CalendarNotConnectedError:
        return {"status": "not_connected", "reply": _NOT_CONNECTED_REPLY}

    return {"status": "executed", "reply": reply}


def decline_pending(session: HasPendingAction) -> dict:
    """Drop a held proposal without writing anything."""
    session.pending_calendar_action = None
    return {"status": "declined", "reply": "Okay, I won't change your calendar."}
