"""
LLM Provider — Claude (claude-sonnet-4-6) or GPT-4o
Injects persona system prompt, uses memory for context.
"""

import os
import httpx
from typing import Any

from memory.manager import MemoryManager


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
        engine:                 'claude' | 'gpt4o'  (defaults to LLM_ENGINE env var)
        system_prompt_override: if provided, replaces the auto-built prompt

    Returns:
        Reply text string
    """
    engine = engine or os.getenv("LLM_ENGINE", "claude")

    if system_prompt_override:
        system_prompt = system_prompt_override
    else:
        # Fallback: build a minimal prompt from persona dict
        from persona.prompt_builder import build_system_prompt
        system_prompt = build_system_prompt(persona)

    messages = memory.get_messages() + [{"role": "user", "content": user_message}]

    if engine == "claude":
        return await _call_claude(system_prompt, messages)
    elif engine == "gpt4o":
        return await _call_gpt4o(system_prompt, messages)
    else:
        raise ValueError(f"Unknown LLM engine '{engine}'. Use 'claude' or 'gpt4o'.")


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
