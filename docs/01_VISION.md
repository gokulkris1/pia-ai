# Pia — Vision & Product Narrative

## The one-liner

Pia is a voice-first personal AI chief-of-staff that orchestrates a personal ecosystem of
specialized agents. You talk to Pia; she directs the agents underneath her. She is loyal
to *you*, not to any single AI model or vendor.

## Positioning: Chief of Agents for People

Pia is **not an agent — Pia is your Chief Agent.** Like a Chief of Staff, but for your
entire digital life. She sits *above* all other agents: she knows you, chooses the right
brain (model), calls the right tool, uses the right device, and coordinates everything
quietly on your behalf.

Brand line: **"Another You. Everywhere."**

What Pia commands (the north-star hierarchy — most of this is far-future, not M1):

```
User
  ↓
PIA — Chief Agent / personal AI OS
  ↓
Specialist agents
  ├── Calendar   ├── Email/Comms   ├── Travel   ├── Home
  ├── Health     ├── Shopping      ├── Work/QA  └── Finance
  ↓
Tools, APIs, devices, sensors, apps
```

| Layer | Examples |
| --- | --- |
| **Brains** | Claude, GPT, Gemini, local models |
| **Senses** | mic, camera, location, health sensors, smart home |
| **Actions** | calendar, email, shopping, reminders, maps, device control |
| **Memory** | personal context, habits, preferences, life timeline |
| **Devices** | phone, desktop, glasses, watch, ring, car, speakers |
| **Specialist agents** | travel, finance, QA, parenting, home, … |

This lifts Pia above the crowded "AI assistant" market. **Important:** this is the
destination, not the next sprint. The orchestrator that realizes this hierarchy is
Milestone 3. The way to actually arrive here without abandoning the project a fifth time is
to ship one real agent (calendar) end-to-end first. See `04_BUILD_ORDER.md`.

## The real idea (and why now)

The original idea dates to 2024 — a presence-aware personal AI. The market has since
filled with "Jarvis" clones, but almost all of them are thin voice wrappers around a
single chatbot. They demo well and do little.

Pia is the opposite bet: not a clever demo, but the **operating system for a person's
agent ecosystem**. The analogy:

- iPhone was the platform; apps were the ecosystem.
- **Pia is the platform; agents are the ecosystem.**

Every agent that enters your life — work, health, lifestyle, creative — plugs into Pia.
Pia already knows your context, preferences, and commitments, so each new agent inherits
that understanding. You never manage 50 agents. You just talk to Pia.

## The moat

The moat is **Pia knowing you better than any single agent ever could**. A standalone
nutrition app knows your food. Pia knows your food *and* your calendar *and* your travel
*and* your goals — so she coordinates across them. That cross-context memory is the defensible thing.

## Business model (later — not Milestone 1)

Proven first on the founder, then on a small number of high-value individuals (the way
boutique "AI agent for CEOs" consultancies operate today). Longer term: third-party agent
builders plug into Pia's ecosystem, and Pia takes a cut of agents that run through her —
an agent marketplace with the cross-context moat at its center. **None of this is built
now. It is context for why the architecture must support many agents later.**

## Founder as user zero

The founder builds Pia for himself first: his own accounts, diary, personal life,
projects, health, year-long to-do list, bookings. A founder who lives inside their own
agent OS daily is the most credible version of this product. Build for one real user
(the founder) before generalizing.

## The "super assistant" trap (important)

"Super assistant that does everything" is a roadmap, not a product. Earlier attempts
stalled by trying to build the whole surface at once. The discipline: Pia must be
genuinely excellent at **one thing people would pay for today**, then expand. The first
"one thing" is the calendar/chief-of-staff loop. See `04_BUILD_ORDER.md`.

## Omnipresence (the long arc)

Pia is mobile-only for now, but the design intent is omnipresence — the same Pia across
phone, watch, car, audio, and AR. This is *why* the interface is an orb and not an
avatar: an orb is the one identity that scales to any surface and any size. The orb on a
phone and a tiny breathing dot on a watch are the same soul. Do not build for hardware we
don't have yet — but don't make choices that would prevent that future either (e.g. keep
the orb resolution- and size-agnostic).
