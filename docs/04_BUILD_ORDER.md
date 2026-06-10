# Pia — Build Order (read this twice)

## Why this document exists

Pia has been started and abandoned multiple times. Every failure had the same cause:
**scope expanded before anything worked end to end.** The vision is big and seductive, and
each restart tried to build the whole surface — all agents, the router, autonomy modes —
at once. That is the enemy. This document is the antidote. Follow it in order. Do not skip
ahead. Each layer is *earned* by shipping the one below it.

---

## Milestone 1 — The spine (CURRENT)

The smallest thing that is actually Pia, working on the founder as user zero. Talkback +
Calendar, shipped together (they're not separable: talkback with nothing to act on is a
toy; calendar with no voice isn't Pia).

**The loop:**
> tap orb → speech-to-text → (one hardcoded model) → understand calendar intent →
> read/write Google Calendar → text-to-speech → orb animates while speaking.

**Sub-steps, in this order:**
1. **Voice loop with stubs.** Mic capture → STT → hardcoded model reply → TTS → orb
   reacts. No calendar yet. Prove the pipe is alive and feels responsive.
2. **Calendar read (real OAuth).** "What's on my calendar tomorrow?" → reads correctly.
   This is the piece that has failed before; get it solid.
3. **Calendar write behind ask-first.** "Move my 3pm to 4:30" → Pia proposes → founder
   confirms → event changes in Google Calendar.

**Out of scope for M1 (do not build):** any second agent; multi-model routing (one model
hardcoded, behind a `chooseModel()` seam); autonomous mode (ask-first only); compare-mode;
memory beyond a single conversation; the agents panel and autonomy settings panels.

**Done when:** every box in `00_GRAND_PROMPT.md`'s "Definition of done" is checked and the
founder uses it on his real calendar.

---

## Milestone 2 — Trust & a second agent (LATER)

Only after M1 works on the founder daily.
- Add per-agent autonomy UI (read-only / ask-first / autonomous) — graduate Calendar to
  autonomous if trusted.
- Add agent #2 (likely Comms — email/WhatsApp triage), in ask-first.
- Persistent memory of commitments across sessions.

## Milestone 3 — The brain router (LATER)

- Replace the hardcoded model with real multi-model routing (Axis 1).
- Token optimization: context trimming, caching, history compression.
- Compare-mode UI ("show me both") and model-pinning preferences.

## Milestone 4 — Ecosystem (MUCH LATER)

- More agents (tasks, finance, health, projects, bookings).
- The agent-marketplace / third-party plug-in direction.
- First non-founder users.

## Milestone 5 — Omnipresence (HORIZON)

- Second surface after mobile (wearable / car / audio — TBD).
- Same orb identity scaled to the new surface.

---

## The single rule that prevents another abandonment

> If you are about to build something that is not in the current milestone, STOP.
> Write it down in the relevant later-milestone section and return to the current one.
> Shipping one layer that works beats four layers that half-work. That is the whole game.
