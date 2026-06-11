"""
LLM Provider — Claude → GPT-4o → Gemini fallback chain.
Injects persona system prompt, uses memory for context.
"""

import json
import os
import httpx
from typing import Any, AsyncIterator

from memory.manager import MemoryManager

# Fallback order when a provider fails or has no key
_FALLBACK_CHAIN = ["claude", "gpt4o", "gemini"]


def _env_value(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value else None


async def generate_response(
    user_message: str,
    persona: dict[str, Any],
    memory: MemoryManager,
    engine: str | None = None,
    system_prompt_override: str | None = None,
) -> str:
    """
    Generate a persona-aware AI reply.

    Args:
        user_message:           what the user just said
        persona:                loaded persona dict
        memory:                 conversation memory for this session
        engine:                 'claude' | 'gpt4o' | 'gemini'  (defaults to LLM_ENGINE env var)
        system_prompt_override: if provided, replaces the auto-built prompt

    Returns:
        Reply text string
    """
    engine = engine or os.getenv("LLM_ENGINE", "gpt4o")

    if system_prompt_override:
        system_prompt = system_prompt_override
    else:
        from persona.prompt_builder import build_system_prompt
        system_prompt = build_system_prompt(persona)

    messages = memory.get_messages() + [{"role": "user", "content": user_message}]

    # Build the ordered list of providers to try, starting from the requested engine.
    start = _FALLBACK_CHAIN.index(engine) if engine in _FALLBACK_CHAIN else 0
    providers = _FALLBACK_CHAIN[start:]

    last_err: Exception | None = None
    for provider in providers:
        try:
            if provider == "claude":
                return await _call_claude(system_prompt, messages)
            elif provider == "gpt4o":
                return await _call_gpt4o(system_prompt, messages)
            elif provider == "gemini":
                return await _call_gemini(system_prompt, messages)
        except Exception as err:
            print(f"[llm] {provider} failed ({err}) — trying next provider")
            last_err = err

    raise RuntimeError(f"All LLM providers failed. Last error: {last_err}")


# ── Claude ────────────────────────────────────────────────────────────────────

async def _call_claude(system_prompt: str, messages: list[dict]) -> str:
    api_key = _env_value("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set in environment")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":          api_key,
                "anthropic-version":  "2023-06-01",
                "content-type":       "application/json",
            },
            json={
                "model":      "claude-sonnet-4-6",
                "max_tokens": 300,
                "system":     system_prompt,
                "messages":   messages,
            },
        )

    if resp.status_code != 200:
        raise ValueError(f"Claude API error {resp.status_code}: {resp.text}")

    data = resp.json()
    return data["content"][0]["text"].strip()


# ── GPT-4o ────────────────────────────────────────────────────────────────────

async def _call_gpt4o(system_prompt: str, messages: list[dict]) -> str:
    api_key = _env_value("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in environment")

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "content-type":  "application/json",
            },
            json={
                "model":      "gpt-4o",
                "max_tokens": 300,
                "messages":   full_messages,
            },
        )

    if resp.status_code != 200:
        raise ValueError(f"GPT-4o API error {resp.status_code}: {resp.text}")

    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


# ── Gemini ────────────────────────────────────────────────────────────────────

async def _call_gemini(system_prompt: str, messages: list[dict]) -> str:
    api_key = _env_value("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment")

    # Convert messages to Gemini's `contents` format (alternating user/model turns)
    contents: list[dict] = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 300, "temperature": 0.7},
    }

    model = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers={"content-type": "application/json"})

    if resp.status_code != 200:
        raise ValueError(f"Gemini API error {resp.status_code}: {resp.text}")

    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


# ── Streaming (realtime voice shim) ─────────────────────────────────────────────
#
# Additive: `generate_response` above is unchanged and still backs the classic
# loop. `stream_response` powers the Vapi custom-LLM path. It yields provider-
# agnostic events so the shim can re-emit them as OpenAI SSE chunks:
#   {"type": "text", "text": "..."}                      incremental tokens
#   {"type": "tool_call", "id", "name", "arguments"}     a model tool/function call
#   {"type": "done", "finish_reason": "stop"|"tool_calls"}
#
# The brain selection (claude → gpt4o → gemini) is identical to generate_response.


async def stream_response(
    system_prompt: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    engine: str | None = None,
    max_tokens: int = 512,
) -> AsyncIterator[dict]:
    """Stream a persona-aware reply, honouring the same provider fallback chain.

    ``messages``/``tools`` are in OpenAI Chat Completions shape (what Vapi sends).
    """
    engine = engine or os.getenv("LLM_ENGINE", "gpt4o")
    start = _FALLBACK_CHAIN.index(engine) if engine in _FALLBACK_CHAIN else 0
    providers = _FALLBACK_CHAIN[start:]

    last_err: Exception | None = None
    for provider in providers:
        try:
            if provider == "claude":
                async for ev in _stream_claude(system_prompt, messages, tools, max_tokens):
                    yield ev
                return
            if provider == "gpt4o":
                async for ev in _stream_gpt4o(system_prompt, messages, tools, max_tokens):
                    yield ev
                return
            if provider == "gemini":
                text_msgs = [m for m in messages if isinstance(m.get("content"), str)]
                text = await _call_gemini(system_prompt, text_msgs)
                yield {"type": "text", "text": text}
                yield {"type": "done", "finish_reason": "stop"}
                return
        except Exception as err:  # noqa: BLE001 — fall back to next provider
            print(f"[llm-stream] {provider} failed ({err}) — trying next provider")
            last_err = err

    raise RuntimeError(f"All streaming LLM providers failed. Last error: {last_err}")


def _openai_tools_to_anthropic(tools: list[dict] | None) -> list[dict]:
    out: list[dict] = []
    for t in tools or []:
        fn = t.get("function", t)
        out.append(
            {
                "name": fn.get("name"),
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
            }
        )
    return out


def _openai_messages_to_anthropic(messages: list[dict]) -> list[dict]:
    """Translate OpenAI-shaped messages (incl. tool calls/results) to Anthropic blocks."""
    out: list[dict] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            continue  # persona system prompt is supplied separately and is authoritative
        if role == "tool":
            out.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": m.get("tool_call_id"),
                            "content": str(m.get("content", "")),
                        }
                    ],
                }
            )
            continue
        if role == "assistant" and m.get("tool_calls"):
            blocks: list[dict] = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in m["tool_calls"]:
                fn = tc.get("function", {})
                raw = fn.get("arguments")
                try:
                    parsed = json.loads(raw) if isinstance(raw, str) else (raw or {})
                except (ValueError, TypeError):
                    parsed = {}
                blocks.append(
                    {"type": "tool_use", "id": tc.get("id"), "name": fn.get("name"), "input": parsed}
                )
            out.append({"role": "assistant", "content": blocks})
            continue
        content = m.get("content")
        if content is None:
            continue
        out.append({"role": role, "content": content})

    # Anthropic requires the conversation to begin with a user turn.
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


async def _stream_claude(
    system_prompt: str, messages: list[dict], tools: list[dict] | None, max_tokens: int
) -> AsyncIterator[dict]:
    api_key = _env_value("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set in environment")

    payload: dict[str, Any] = {
        "model": "claude-sonnet-4-6",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": _openai_messages_to_anthropic(messages),
        "stream": True,
    }
    if tools:
        payload["tools"] = _openai_tools_to_anthropic(tools)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST", "https://api.anthropic.com/v1/messages", headers=headers, json=payload
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise ValueError(f"Claude stream error {resp.status_code}: {body[:300]!r}")

            cur_tool: dict | None = None
            stop_reason = "stop"
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data:
                    continue
                try:
                    evt = json.loads(data)
                except ValueError:
                    continue
                etype = evt.get("type")
                if etype == "content_block_start":
                    blk = evt.get("content_block", {})
                    if blk.get("type") == "tool_use":
                        cur_tool = {"id": blk.get("id"), "name": blk.get("name"), "args": ""}
                elif etype == "content_block_delta":
                    d = evt.get("delta", {})
                    if d.get("type") == "text_delta":
                        text = d.get("text", "")
                        if text:
                            yield {"type": "text", "text": text}
                    elif d.get("type") == "input_json_delta" and cur_tool is not None:
                        cur_tool["args"] += d.get("partial_json", "")
                elif etype == "content_block_stop" and cur_tool is not None:
                    yield {
                        "type": "tool_call",
                        "id": cur_tool["id"],
                        "name": cur_tool["name"],
                        "arguments": cur_tool["args"] or "{}",
                    }
                    cur_tool = None
                elif etype == "message_delta":
                    if evt.get("delta", {}).get("stop_reason") == "tool_use":
                        stop_reason = "tool_calls"

            yield {"type": "done", "finish_reason": stop_reason}


async def _stream_gpt4o(
    system_prompt: str, messages: list[dict], tools: list[dict] | None, max_tokens: int
) -> AsyncIterator[dict]:
    api_key = _env_value("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in environment")

    payload: dict[str, Any] = {
        "model": "gpt-4o",
        "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools

    headers = {"Authorization": f"Bearer {api_key}", "content-type": "application/json"}
    tool_acc: dict[int, dict] = {}

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST", "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise ValueError(f"GPT-4o stream error {resp.status_code}: {body[:300]!r}")

            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    evt = json.loads(data)
                except ValueError:
                    continue
                choice = (evt.get("choices") or [{}])[0]
                delta = choice.get("delta", {})
                if delta.get("content"):
                    yield {"type": "text", "text": delta["content"]}
                for tc in delta.get("tool_calls", []) or []:
                    idx = tc.get("index", 0)
                    acc = tool_acc.setdefault(idx, {"id": None, "name": "", "args": ""})
                    if tc.get("id"):
                        acc["id"] = tc["id"]
                    fn = tc.get("function", {})
                    if fn.get("name"):
                        acc["name"] += fn["name"]
                    if fn.get("arguments"):
                        acc["args"] += fn["arguments"]

    for acc in tool_acc.values():
        yield {
            "type": "tool_call",
            "id": acc["id"],
            "name": acc["name"],
            "arguments": acc["args"] or "{}",
        }
    yield {"type": "done", "finish_reason": "tool_calls" if tool_acc else "stop"}
