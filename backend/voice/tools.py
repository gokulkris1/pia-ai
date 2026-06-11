"""Vapi server-tool dispatch for calendar actions.

Vapi calls our secured ``/api/voice/tools/calendar`` webhook when the model
emits a tool call. Each tool maps onto the SHARED ask-first gate
(``calendar_agent.service``) — the exact same propose → confirm → execute path
the classic HTTP routes use. Writes are never executed without a prior proposal
and an explicit confirmation.

State (the pending proposal) lives in the per-call ``VoiceSession`` keyed by the
Vapi ``call.id``.
"""

from __future__ import annotations

import os
from pathlib import Path

from calendar_agent import service as calendar_service
from voice import sessions

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _user_id() -> str:
    return os.getenv("PIA_USER_ID", "default")


def _timezone() -> str:
    return os.getenv("PIA_TIMEZONE", "Europe/Dublin")


# OpenAI-function-shaped definitions, surfaced to Vapi so the model knows the
# calendar tools and their args. The names match `dispatch` below.
TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "read_calendar",
            "description": "Read the user's Google Calendar for a natural-language time window "
            "(e.g. 'today', 'tomorrow', 'this week'). Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural-language window, e.g. \"what's on tomorrow\".",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_event",
            "description": "Propose a calendar CHANGE (create, move, or cancel). Does NOT write. "
            "Returns a confirmation prompt to read back to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The user's full instruction, e.g. 'move my 3pm to 4pm' "
                        "or 'book a dentist appointment Friday at 10am'.",
                    }
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_event",
            "description": "Confirm or decline the pending proposed calendar change. Only call "
            "this AFTER the user has clearly said yes or no.",
            "parameters": {
                "type": "object",
                "properties": {
                    "confirmation": {
                        "type": "string",
                        "description": "The user's answer, e.g. 'yes' or 'no'.",
                    },
                    "proposal_id": {
                        "type": "string",
                        "description": "Optional id of the proposal being confirmed.",
                    },
                },
                "required": ["confirmation"],
            },
        },
    },
]


def dispatch(call_id: str, name: str, arguments: dict) -> str:
    """Run one calendar tool call through the shared gate. Returns spoken-text result."""
    user_id = _user_id()
    session = sessions.get_or_create(call_id)

    if name == "read_calendar":
        query = arguments.get("query") or "what's on my calendar today"
        return calendar_service.read_calendar(PROJECT_ROOT, user_id, query, _timezone())["reply"]

    if name == "propose_event":
        text = arguments.get("text") or ""
        if not text.strip():
            return "What change would you like me to make to your calendar?"
        return calendar_service.propose_change(
            PROJECT_ROOT, user_id, session, text, _timezone()
        )["reply"]

    if name == "confirm_event":
        confirmation = arguments.get("confirmation") or ""
        proposal_id = arguments.get("proposal_id")
        return calendar_service.confirm_pending(
            PROJECT_ROOT, user_id, session, confirmation, proposal_id
        )["reply"]

    return f"Unknown calendar tool: {name}"
