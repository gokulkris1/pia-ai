# Pia — Agent Architecture (hierarchy, templates, cross-device, onboarding)

North-star architecture. Most of this is target-state, pinned to later milestones. Captured
so it's preserved and dated — NOT a backlog. You'll build ~3-4 of these agents in the next
year. The list's job is to make the few you build have clean seams toward the rest.

---

## The core principle: connected, not fat

**The fat-vs-connected smell (trust this instinct):** if adding an agent means editing Pia's
code, you're building features into a monolith and calling them agents. Pia is getting fat,
not connected.

- **Fat Pia (wrong):** Pia *contains* calendar/nutrition/bills logic as functions inside her.
  To add an agent you edit Pia. She knows how to do everything herself. A monolith in a costume.
- **Connected Pia (right):** Pia contains almost nothing about any domain. She's a thin,
  brilliant router + relationship — she knows *you*, holds context, decides what matters, and
  *delegates* to agents that live as their own separate things with a clean contract.

**The test:** can you add a new agent WITHOUT editing Pia's code? If no → it's fat. Fix it now,
at agent two, not at agent eight when separating the monolith is a six-month nightmare.

**The principle to hold:** Pia gets smarter about *you* and dumber about *tasks*. Task-knowledge
in Pia = fat. Her job is to know you, hold context, decide, delegate. Agents hold task-knowledge.
The day Pia knows nothing about *how* to check a calendar but everything about *when you'd want
to* — that's connected Pia, and it scales to fifty agents and a marketplace.

---

## The agent contract (the "outside" Pia sees — identical for all agent types)

Every agent — plugged, custom-built, or synthesised — presents the SAME outward contract:
- **Capabilities** — what can I do? (so Pia knows when to call it)
- **Actions** — do this specific thing (with ask-first gating for anything sensitive)
- **Memory** — what do I know / what did I do (stored centrally, never on-device)

Pia only ever sees the outside. She does not know or care whether the calendar agent is custom
code, the mythology agent is a curated knowledge domain, or the photo agent is a third party.
The contract is the agent's *outside*; the MCP/domain is its *inside*. This identical-outside
property is what makes the marketplace and the hierarchy possible.

---

## Agent domains (the "inside"): the three fulfillment types

Each agent has a bounded **domain** — the world it can reach (tools, documents, services, sites).
The boundary IS the identity: a mythology agent is mythology *because* its world is bounded to
mythology sources. Scope tightly. But how you fulfill the domain varies — don't hand-build an
MCP for every agent:

1. **Off-the-shelf / plugged** — the agent brings its OWN MCP/domain. You're the consumer; you
   just choose to trust it and what it can touch. (Their breadth is their problem.)
2. **Synthesised** — built over EXISTING services/MCPs/APIs. e.g. bills, calendar. The agent is
   a thin layer of *judgment* over connectors that already exist. You compose, you don't author.
3. **Custom domain** — no off-the-shelf MCP exists. e.g. a Greek/Indian mythology agent over
   YOUR collection. Here you genuinely author a small MCP: curate sources, define tools, point
   at your documents. This is the minority case, not every agent.

**Decision guide — author vs compose:** Does a service/API/MCP already exist for this domain?
Compose it (type 2). Does the agent just wrap someone's published agent? Plug it (type 1). Is
the domain your own curated knowledge with no existing service? Author an MCP (type 3).

**Two control dials (keep separate):**
- **Breadth** — controlled by the agent's domain/MCP boundary (what it *can reach*).
- **Trust** — controlled by Pia's per-agent autonomy ladder (what it's *allowed to do*):
  read-only / ask-first / autonomous.

---

## The agent templates (~6 types)

Your three prototypes (below) cover most. The full set:
1. **Off-the-shelf** — consume an external agent/MCP.
2. **Synthesised** — judgment layer over existing services (calendar, bills).
3. **Custom-domain** — authored MCP over your own collection (mythology).
4. **Proactive/monitor** — not asked; watches the world and surfaces (weather alert, "your bill
   went up", news capsule). Distinct because triggered by the world, not you. IMPORTANT: this is
   your differentiation — proactivity is what chatbots don't do. Build this template early-ish.
5. **Pure-LLM** — no tools, no domain, just reasoning (thinking partner, writing). Trivial; needs
   no MCP.
6. **Multi-step / workflow** — chains actions across other agents to complete a job (travel =
   calendar + bookings + weather + bills). These are proto-choreographers — the seed of the
   mid-layer hierarchy. They mature INTO the hierarchy.

---

## The first three prototypes (prove one of each type, in this order)

Goal is THREE PROVEN PATTERNS, not three agents. Once a pattern works and you'd use it, move on.
Finish each before starting the next.

1. **Nutrition (synthesised)** — FIRST. Agent two, real daily utility, establishes the agent
   contract on the agent you'll actually use. Centerpiece = the proactive check-in (the magic
   that makes it a relationship, not a log). Everything else inherits this contract.
2. **Mythology (custom-domain)** — SECOND. The sharpest architecture test: domain is YOUR
   collection, almost no "service." Proves Pia can talk to a bounded authored-knowledge domain.
   Low-stakes (wrong answer moves no calendar, touches no money) = perfect safe sandbox for the
   riskiest pattern. Also FORCES connected architecture: you literally can't build it "into" Pia,
   so it's the medicine for the fat feeling.
3. **Off-the-shelf** — THIRD. Easiest, least risk, depends least on you. Proves Pia's contract is
   general enough to wrap an external agent she didn't author. The victory lap.

Order rationale: nutrition establishes the contract + utility; mythology proves custom-domain
safely and enforces connectedness; off-the-shelf proves external plug. Each finished before next.

---

## Cross-device: brain in the cloud, device is a window

The differentiating technical moat. Principle: **agents and memory live in the cloud (your
backend), NEVER on the device.** The device is just a window — a way to see and talk to Pia.
Phone, watch, car, glasses are thin clients rendering the same cloud-side Pia. (This is why the
orb was right: one identity that re-renders at any size on any surface while the brain stays
central.)

So "switch phone → car and keep context" is not a sync problem — it's a consequence of the
architecture. Nothing lives on the phone to sync. The session was never on the phone; the car's
Pia is the same session because context was always central.

What adapts per device is the *presentation and appropriateness*, not the brain:
- **Phone** — full Pia, home base, richest interaction.
- **Watch** — glanceable, voice-first, quick confirms. Pia compressed, not diminished.
- **Car** — voice-only, hands-free, safety-shaped; she knows you're driving and behaves shorter.
- **Glasses/AR** — ambient, spatial, the long-horizon "just present" surface.
- **Desktop** — work mode, more text, more depth.

**Cheap insurance to build now:** every agent exposes the same contract (capabilities/actions/
memory) AND stores memory centrally, never on-device. Do this and any agent works on any device
automatically, and any future choreography layer can coordinate them.

---

## Agent onboarding: manual now, auto-discovery later, connection ALWAYS ask-first

Should Pia, in auto mode, connect to a NEW agent on her own when no existing agent can do a job?

**Answer: yes, but the connection itself is an ask-first action.** Auto-connecting unvetted code
that gets access to your life is the single most dangerous thing Pia could do — it's the inverse
of the trust model. So:
1. Pia hits a job no existing agent can do.
2. In auto mode she may *search and propose*: "I don't have an agent for this; I found one that
   can. It needs access to X. Connect it?"
3. **You approve the connection (once).** Discovery/recommendation is autonomous; *granting
   access* is ask-first.
4. The agent is then yours, at whatever autonomy you assign.

Same shape as the calendar model: propose → confirm → execute. "Connect a new agent" is just the
highest-stakes write there is. Auto-discovery, ask-first connection — that's the line.

**Carve-out:** distinguish *connecting a new agent* (high stakes, always ask-first) from *using a
tool within an already-approved agent's domain* (low stakes, can be autonomous if that agent is
set autonomous). Keep these distinct or Pia is either annoying or dangerous.

**Sequencing:** manual now (you plug in nutrition/mythology/off-the-shelf by hand, deliberately).
Auto-discovery is Milestone 3-4 — it requires the marketplace to exist first. Because every agent
honors the same contract, auto-onboarding later is just "do the manual plug-in automatically" —
nearly free once the marketplace exists. This is WHY the contract matters so much now.

---

## The layered hierarchy (target state, ~Milestone 4-5 — do NOT build now)

The destination, captured. Arrives only when flat routing genuinely breaks (≈agent 6-8), built
from real friction, not a diagram:
- **Edge agents** — do one concrete task in one app. The hands.
- **Mid-level agents** — operate an app end-to-end; choreograph edge agents. The limbs.
- **Choreographic layer** — cross-compares/synthesizes across domains; the "put my thought into
  it" layer. (Grows out of the type-6 workflow agents.)
- **Leaders** — make domain decisions, report up.
- **Pia** — decides like you would, across everything. The top of the tree.

**Build order when the time comes:** flat agents until routing hurts → add choreography layer
ABOVE existing flat agents (your flat agents become edge agents) → add leaders when multiple
choreographers need to report up → Pia becomes true delegator → "every app is an agent" /
third-party marketplace.

**The rule that prevents premature hierarchy:** a four-layer hierarchy with two agents in it is
an org chart for a company of three. Structure is pure overhead until volume justifies it. Flat
first, layer when flat breaks. Every flat agent teaches you what the choreography layer actually
needs — you'll design a far better hierarchy at agent eight than now.
