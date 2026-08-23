# Pia — The Agent Contract (technical spec)

The minimal interface every agent honors so Pia can talk to all of them identically — whether
custom-built, synthesised, or plugged. This is the "outside" every agent presents. Defined now
(at agent two) so the pattern is right from the second instance, not retrofitted from the eighth.

> Scope discipline: this defines a LIGHT contract and a registry, not a full agent platform.
> Do NOT build a marketplace, protocol spec, or discovery engine now. Build the thin contract,
> make nutrition the first agent that honors it, register it (registry may have 1-2 entries).
> The platform comes later; the *pattern* comes now.

---

## What Pia holds vs what the agent holds

- **Pia holds:** you (context, preferences, history), the decision of *which* agent to call and
  *when*, the autonomy/permission level per agent, and the conversation.
- **The agent holds:** all task-knowledge for its domain, its tools/sources (its MCP/domain),
  and how to actually do the thing.

Pia must remain ignorant of *how* any agent does its job. She knows only the contract below.

---

## The contract: three surfaces

### 1. Capabilities (discovery)
The agent declares what it can do, in a form Pia can match intent against. Enough for Pia to
decide "this request belongs to the nutrition agent." Includes: a name/id, a short description,
and a list of capability descriptors (e.g. "log food intake", "summarise today's nutrition",
"check in on goals").

### 2. Actions (execution, with ask-first gating)
Pia calls an action with parameters. Each action declares its **sensitivity**:
- **read** — silent, no confirmation (e.g. "what did I eat today").
- **write / sensitive** — requires ask-first: agent returns a *proposal*; Pia surfaces it; user
  confirms; only then the action executes. (Reuse the calendar propose→confirm→execute gate —
  do NOT invent a new trust model.)

The confirmation must be an ENFORCED gate (backend-verified against a real pending proposal),
not a frontend convention — same lesson as the calendar confirm-gate fix.

### 3. Memory (central, never on-device)
The agent reads/writes its memory through a central store keyed to the user, so:
- context survives across devices (brain in cloud, device is a window),
- Pia can pull cross-agent context (the nutrition agent's data is available when the calendar
  agent's dinner event matters — this cross-domain awareness is the "knows me" magic).

---

## The registry (thin, now)

A simple registry maps capabilities → agent, so Pia can route. Now it has 1-2 entries and is
basically a lookup. Later it's how auto-discovery/onboarding works (manual now, auto + ask-first
later — see 09_AGENT_ARCHITECTURE.md). The point of defining it now: adding an agent should be
*registering* it, not editing Pia. That's the test of connected-not-fat.

---

## Why this exact shape

- **Identical outside → marketplace + hierarchy possible.** Custom, synthesised, and plugged
  agents all look the same to Pia, so she (and later a choreography layer) can coordinate any of
  them.
- **Ask-first baked into actions → trust model is uniform.** Every sensitive action across every
  agent uses the same propose→confirm→execute gate the calendar already proved.
- **Central memory → cross-device + cross-agent.** The two hardest, most differentiating
  properties fall out of the contract instead of being special-cased.
- **Registry not editing → connected not fat.** Enforces the architecture that keeps Pia thin.

---

## For the build: nutrition is the reference implementation

Nutrition (agent two) is built as the FIRST agent honoring this contract — as a separate module,
not baked into Pia. Calendar can stay as-is for now (it works; don't break it), but nutrition
establishes the pattern. Once nutrition honors the contract cleanly, mythology and off-the-shelf
inherit it, and every future agent is "copy the template."
