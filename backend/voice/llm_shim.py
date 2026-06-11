"""OpenAI-compatible custom-LLM shim for Vapi.

Vapi treats this as an OpenAI Chat Completions provider: it POSTs
``{messages, tools, stream, ...}`` and consumes a streamed SSE response. We use
that seam to keep the BRAIN ours — the persona system prompt is injected
server-side (authoritative; Vapi's own system text is ignored) and the reply is
produced by ``chooseModel()`` → Claude via ``stream_response``. The orchestrator
(Vapi) never reasons; it only does ears (STT) and mouth (TTS).

Tool calls flow through transparently: if the model emits a calendar tool call,
we surface it as OpenAI ``tool_calls`` so Vapi dispatches to our secured
``/api/voice/tools/calendar`` webhook.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, AsyncIterator

from providers.llm import stream_response
from persona.prompt_builder import build_system_prompt
from users.loader import load_user_profile

_VOICE_TOOL_GUIDANCE = (
    "\n\nYou are speaking out loud in a live phone-style call, so keep replies short, "
    "warm, and natural. You can manage the user's Google Calendar using the provided "
    "tools. For anything that READS the calendar, just do it. For anything that WOULD "
    "CHANGE the calendar (create, move, cancel), you MUST first call the calendar tool "
    "to PROPOSE the change, read back the proposal, and only confirm after the user "
    "clearly says yes. Never confirm a change the user did not explicitly approve."
)


def persona_system_prompt(user_id: str) -> str:
    """Build Pia's authoritative voice-mode system prompt for this user."""
    profile = load_user_profile(user_id)
    return build_system_prompt(profile.persona, mode="call") + _VOICE_TOOL_GUIDANCE


def _chunk(payload: dict, model: str, completion_id: str, created: int) -> str:
    body = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [payload],
    }
    return f"data: {json.dumps(body)}\n\n"


async def stream_openai_chunks(
    messages: list[dict],
    tools: list[dict] | None,
    user_id: str,
    model: str = "pia-voice",
) -> AsyncIterator[str]:
    """Yield OpenAI-format SSE chunks Vapi can stream straight to TTS."""
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    system_prompt = persona_system_prompt(user_id)

    # Opening chunk establishes the assistant role.
    yield _chunk(
        {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None},
        model,
        completion_id,
        created,
    )

    finish_reason = "stop"
    tool_index = 0
    try:
        async for ev in stream_response(system_prompt, messages, tools=tools):
            etype = ev.get("type")
            if etype == "text":
                yield _chunk(
                    {"index": 0, "delta": {"content": ev["text"]}, "finish_reason": None},
                    model,
                    completion_id,
                    created,
                )
            elif etype == "tool_call":
                yield _chunk(
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": tool_index,
                                    "id": ev.get("id") or f"call_{uuid.uuid4().hex[:8]}",
                                    "type": "function",
                                    "function": {
                                        "name": ev.get("name"),
                                        "arguments": ev.get("arguments") or "{}",
                                    },
                                }
                            ]
                        },
                        "finish_reason": None,
                    },
                    model,
                    completion_id,
                    created,
                )
                tool_index += 1
            elif etype == "done":
                finish_reason = ev.get("finish_reason", "stop")
    except Exception as err:  # noqa: BLE001 — never crash the live call
        print(f"[voice-llm] stream error: {err}")
        yield _chunk(
            {
                "index": 0,
                "delta": {"content": "Sorry — I hit a snag just then. Could you say that again?"},
                "finish_reason": None,
            },
            model,
            completion_id,
            created,
        )
        finish_reason = "stop"

    yield _chunk(
        {"index": 0, "delta": {}, "finish_reason": finish_reason},
        model,
        completion_id,
        created,
    )
    yield "data: [DONE]\n\n"


def extract_messages_and_tools(payload: dict[str, Any]) -> tuple[list[dict], list[dict] | None]:
    """Pull OpenAI messages/tools out of whatever Vapi posts (it nests differently)."""
    # Vapi may post the OpenAI body at the top level, or under message/payload.
    body = payload
    if "messages" not in body and isinstance(body.get("message"), dict):
        body = body["message"]
    messages = body.get("messages") or []
    tools = body.get("tools")
    return messages, tools
