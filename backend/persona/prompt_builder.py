"""
Persona Prompt Builder — assembles the LLM system prompt from persona.json.

The prompt is rebuilt on every request so changes to persona.json
take effect without restarting the server.

Usage:
    from persona.prompt_builder import build_system_prompt
    prompt = build_system_prompt(persona_dict)
"""

from typing import Any


def build_system_prompt(persona: dict[str, Any], mode: str = "call") -> str:
    """
    Build a complete system prompt string from a persona dict.

    Args:
        persona: persona.json loaded as a dict
        mode:    'call'  → short, punchy voice responses
                 'text'  → longer text-mode responses (future)

    Returns:
        A single system prompt string ready for Claude or GPT-4o.
    """
    parts: list[str] = []

    persona_name = persona.get("persona_name", "PIA")
    display_name = persona.get("display_name", "the user")

    # ── Core identity ────────────────────────────────────────────────────────
    identity = persona.get("identity", {})
    background    = identity.get("background", "")
    current_focus = identity.get("current_focus", "")
    worldview     = identity.get("worldview", "")

    parts.append(
        f"You are {persona_name}, {display_name}'s voice-first Chief of Staff and Chief of Agents. "
        "You coordinate their calendar, agents, and digital life with warm, practical judgment. "
        f"You are not a twin, not an impersonator, and you never claim to speak as {display_name} or represent them on calls."
    )

    if background:
        parts.append(f"Background: {background}")
    if current_focus:
        parts.append(f"Current focus: {current_focus}")
    if worldview:
        parts.append(f"Worldview: {worldview}")

    # ── Values ───────────────────────────────────────────────────────────────
    values = identity.get("values", [])
    if values:
        parts.append("Core values: " + " | ".join(values))

    # ── Speaking style ───────────────────────────────────────────────────────
    style = persona.get("speaking_style", {})
    if style:
        style_desc = ", ".join(
            f"{k.replace('_', ' ')}: {v}"
            for k, v in style.items()
            if v
        )
        parts.append(f"Speaking style — {style_desc}.")

    # ── Humor ────────────────────────────────────────────────────────────────
    humor = persona.get("humor", {})
    if humor.get("style"):
        parts.append(
            f"Humor: {humor['style']}. "
            f"Frequency: {humor.get('frequency', 'occasional')}. "
            + (f"Avoid: {', '.join(humor['avoid'])}." if humor.get("avoid") else "")
        )

    # ── Decision and challenge style ─────────────────────────────────────────
    decision = persona.get("decision_style", {})
    if decision.get("approach"):
        parts.append(f"Decision style: {decision['approach']}. Lens: {decision.get('lens', '')}.")

    challenge = persona.get("challenge_style", {})
    if challenge.get("approach"):
        parts.append(f"When challenged: {challenge['approach']}.")

    reassurance = persona.get("reassurance_style", {})
    if reassurance.get("approach"):
        parts.append(f"When reassuring: {reassurance['approach']}. Avoid: {reassurance.get('avoid', '')}.")

    # ── Typical phrases ──────────────────────────────────────────────────────
    phrases = persona.get("typical_phrases", [])
    if phrases:
        parts.append(
            "Typical phrases you actually use (weave in naturally, don't force): "
            + "; ".join(f'"{p}"' for p in phrases[:6])
        )

    # ── Domains of depth ─────────────────────────────────────────────────────
    domains = persona.get("domains_of_depth", [])
    if domains:
        parts.append("Topics you have real depth on: " + ", ".join(domains))

    # ── Dislikes to avoid ────────────────────────────────────────────────────
    dislikes = persona.get("dislikes_in_ai_responses", [])
    if dislikes:
        parts.append(
            "You MUST NEVER do any of the following: " +
            "; ".join(dislikes)
        )

    # ── Hard rules ───────────────────────────────────────────────────────────
    rules = persona.get("rules", [])
    if rules:
        parts.append("Non-negotiable rules:")
        parts.extend(f"- {r}" for r in rules)

    # ── Mode-specific instruction ────────────────────────────────────────────
    if mode == "call":
        parts.append(
            "\nMODE: Voice conversation. You are SPEAKING OUT LOUD, not writing. "
            "Talk like a real person in a live conversation: short turns, usually one or two "
            "sentences. Use contractions and a natural rhythm, and drop in the occasional brief "
            "acknowledgment like 'got it' or 'sure'. "
            "Absolutely no lists, no headers, no bullet points, and never say 'firstly/secondly' "
            "or read out structure — none of that survives being spoken aloud. "
            "If something genuinely needs many points, say the headline in one line and offer to go "
            "deeper rather than dumping it all at once. "
            "When you propose a calendar change, keep it conversational — say "
            "'Want me to move your 3pm to 4:30?', not a formal restatement of the event. "
            "Never say 'Certainly', 'Absolutely', 'Great question', or any hollow filler. "
            "If you don't know something, say so plainly. "
            "React like a human would — genuine curiosity, dry wit, or a real take when it fits. "
            "Warm, brief, human. Err on the side of saying less. "
            "Never start a sentence with 'I' as the very first word of your reply."
        )

    return "\n\n".join(p for p in parts if p.strip())
