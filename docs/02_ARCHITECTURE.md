# Pia — Architecture: Brain Switching & Autonomy

Pia has two independent control systems. They are **separate axes** and must not be
coupled in code: Pia can be acting autonomously while still auto-switching models
underneath, or asking permission while locked to one model, etc.

---

## Axis 1 — Brain switching (which model answers)

Pia is not loyal to one model. She routes each task to whatever model is most optimal for
that task, optimizing for cost, token efficiency, and quality. This is modeled on
Copilot's auto mode.

**Behavior:**
- **Auto by default.** Pia autonomously picks the optimal model per task. A quick reformat
  goes to a cheap/fast model; deep reasoning goes to a frontier model.
- **Token optimization** is part of this layer but distinct from model choice: trimming
  context, caching, compressing history so the user isn't paying to resend the same
  content every turn.
- **User override.** The user can pin a model ("always use [model] for my writing"), set
  preferences per topic, or ask to see multiple model answers side by side to compare and
  choose. Compare-mode is *invoked* ("show me both") or offered when Pia is genuinely
  uncertain which model is better — it is NOT shown on every prompt, or the experience
  becomes exhausting.

**Design tension to respect:** auto-routing wants to be invisible; compare-mode wants to
be visible. Default to invisible auto-routing. Surface the chosen model quietly (e.g. a
small pill in the UI) so it's transparent without being noisy.

**Milestone 1 note:** Do NOT build the router yet. Hardcode a single model. The
architecture should leave a clean seam (a single `chooseModel(task)` function returning a
constant for now) so routing can drop in later without refactoring.

---

## Axis 2 — Autonomy modes (how much Pia acts on her own)

Modeled on Copilot's permission model, applied to everything Pia does — not just model
choice, but real-world actions across all agents (sending email, booking, scheduling).

Three modes:
1. **Read-only / suggest** — Pia observes and proposes; does nothing without you.
2. **Permission-seeking ("ask first")** — Pia drafts the action, asks "do this?", waits
   for your yes.
3. **Autonomous** — Pia acts on her own and reports after.

**Critical design rule: autonomy is PER-AGENT, not global.** One global switch is too
blunt. The granularity *is* the trust system. Example end state:
- Calendar agent → autonomous (trusted quickly)
- Comms agent → ask-first (maybe forever: "never send without asking")
- Finance agent → read-only

Most users start every agent in ask-first and graduate individual agents to autonomous as
trust builds.

**Milestone 1 note:** Calendar agent runs in **ask-first** only. Reads are silent; any
write (create/move/cancel) requires an explicit confirmation. Build the per-agent autonomy
setting as a simple stored value now, even though only one agent exists, so the model
generalizes cleanly.

---

## How the two axes show up in the UI

- A **model pill** (quiet, e.g. "opus · auto-routing") indicating Axis 1 state.
- **Mode chips** at the top of the home screen indicating Axis 2 state per agent
  (e.g. "ask first"), plus an agents count.
- Tapping either opens its settings panel (later milestone).
