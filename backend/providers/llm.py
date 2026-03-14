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
    image_base64: str | None = None,
) -> str:
    """
    Generate a persona-aware AI reply.

    Args:
        user_message:           what the user just said
        persona:                loaded persona dict
        memory:                 conversation memory for this session
        engine:                 'claude' | 'gpt4o'  (defaults to LLM_ENGINE env var)
        system_prompt_override: if provided, replaces the auto-built prompt
        image_base64:           optional JPEG frame from back camera for visual context

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
        try:
            return await _call_claude(system_prompt, messages)
        except Exception as claude_err:
            print(f"[llm] Claude failed ({claude_err}) — falling back to GPT-4o")
            return await _call_gpt4o(system_prompt, messages, image_base64=image_base64)
    elif engine == "gpt4o":
        return await _call_gpt4o(system_prompt, messages, image_base64=image_base64)
    else:
        raise ValueError(f"Unknown LLM engine '{engine}'. Use 'claude' or 'gpt4o'.")


# ── Claude ────────────────────────────────────────────────────────────────────

async def _call_claude(system_prompt: str, messages: list[dict]) -> str:
    api_key = os.getenv("calude_key")
    if not api_key:
        raise ValueError("calude_key is not set in environment")

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

async def _call_gpt4o(system_prompt: str, messages: list[dict], image_base64: str | None = None) -> str:
    api_key = os.getenv("OpenAI_Key")
    if not api_key:
        raise ValueError("OpenAI_Key is not set in environment")

    # If an image frame is present, inject it into the last user message as vision content
    if image_base64:
        gpt_messages: list[dict] = []
        for i, m in enumerate(messages):
            if i == len(messages) - 1 and m["role"] == "user":
                # Vision-capable content block — back camera: "here's what I'm looking at"
                gpt_messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": m["content"]},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url":    f"data:image/jpeg;base64,{image_base64}",
                                "detail": "low",   # 'low' = faster + cheaper, enough for context
                            },
                        },
                    ],
                })
            else:
                gpt_messages.append(m)
    else:
        gpt_messages = messages

    full_messages = [{"role": "system", "content": system_prompt}] + gpt_messages

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
