# Pia — NEXT SESSION: Build Nutrition as Agent Two (the connected way)

Do NOT run this in the same session you captured strategy. This is the next build session.
Paste this to Copilot when you're ready to build (after the voice/Vapi work is at a checkpoint).

---

> **Build nutrition as Pia's second agent — but built the CONNECTED way, not baked into Pia.**
> Read `/docs/09_AGENT_ARCHITECTURE.md` and `/docs/11_AGENT_CONTRACT.md` first.
>
> **The architectural requirement (most important):** nutrition must be a SEPARATE agent module
> that honors the agent contract (capabilities / actions / memory), registered with Pia via a
> thin registry — NOT calendar-style logic baked into main.py. The test: I should be able to add
> a future agent by registering it, without editing Pia's core. Calendar can stay as-is for now;
> don't refactor it. Nutrition is the reference implementation of the contract.
>
> **Scope discipline:** build a LIGHT contract + registry (1-2 entries), NOT a marketplace,
> protocol spec, or discovery engine. The pattern now; the platform later.
>
> **What nutrition does in v1 (the core loop that makes it feel alive):**
> 1. I tell Pia what I ate / supplements I took (by voice) → she logs it (central memory).
> 2. I ask what I've had today / how I'm tracking → she reads it back (silent read).
> 3. **The centerpiece — proactive check-in.** Pia checks in with me about food/goals. This is
>    the magic that makes it a relationship, not a log. [CHECK-IN MODEL: _____ — see below, pick one.]
>
> **Check-in model (I'll pick one — fill before building):**
> - (a) Scheduled — a daily "what did you eat today?" at set times. Simplest.
> - (b) Goal-based — I set a goal (e.g. cut sugar); she checks in when she notices a gap.
> - (c) Contextual/cross-domain — she uses my CALENDAR (dinner out tonight) to check in
>   contextually ("you've got dinner with Sarah — how'd it fit your goals?"). This is the
>   cross-agent magic that proves the whole "agents that coordinate" thesis. Hardest, highest value.
>
> **Trust:** anything sensitive uses the ask-first propose→confirm→execute gate (reuse the
> calendar pattern, the enforced backend gate — not a frontend convention). Logging food is a
> low-stakes write; use judgment on what needs confirmation.
>
> **Reuse:** the proven spine — voice in → intent → agent → ask-first if sensitive → voice out;
> orb state wiring; persona. Nutrition data stored centrally (survives devices, available
> cross-agent).
>
> **First, before code:** read the two docs, propose a file-by-file plan showing nutrition as a
> separate contract-honoring module + the thin registry + how it plugs into the existing voice
> loop, and WAIT for my go-ahead. Build on a branch, not main. Finish and let me use it before
> we discuss agent three.

---

## Decision to make before you paste this

**Pick the check-in model (a / b / c).** My co-founder recommendation: if calendar is solid, go
(c) contextual — it's the one that produces a real cross-domain "she knows me" moment and proves
the coordination thesis in a single feature. If you want to ship faster and prove the agent
contract first, start (a) scheduled and upgrade to (c) once the contract is solid. Either is
defensible; (c) is the differentiator, (a) is the faster proof.

## Session sequencing reminder

You currently have TWO build tracks open: the Vapi voice rework (`voice-realtime` branch) and
this nutrition agent. Don't run both at once. Suggested order:
1. Get the UI refresh merged (you were about to preview it on your phone).
2. Decide voice: do the Vapi rework OR defer it.
3. Then nutrition as agent two.
Pick ONE track per session. Parallel tracks = the dilution that stalls momentum.
