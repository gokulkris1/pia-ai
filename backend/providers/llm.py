"""
LLM Provider — Claude → GPT-4o → Gemini fallback chain.
Injects persona system prompt, uses memory for context.
"""

import os
import httpx
from typing import Any

from memory.manager import MemoryManager

# Fallback order when a provider fails or has no key
_FALLBACK_CHAIN = ["claude", "gpt4o", "gemini"]


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
    api_key = os.getenv("ANTHROPIC_API_KEY")
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
    api_key = os.getenv("OPENAI_API_KEY")
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
    api_key = os.getenv("GEMINI_API_KEY")
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
