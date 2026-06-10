# Pia — Grand Build Prompt (paste this into Copilot first)

You are my coding co-pilot building **Pia**, a voice-first personal AI chief-of-staff.
Before writing any code, read every `.md` file in this `/docs` folder. They contain the
full product vision, architecture, design spec, and build order. Do not deviate from the
build order. Do not expand scope beyond the current milestone.

## What we are building RIGHT NOW (Milestone 1 — the spine)

The smallest thing that is actually *Pia*, working end to end on me (the founder) as user zero:

> I tap the orb and talk → Pia transcribes my speech → routes it to an LLM → Pia
> understands calendar intent → reads/writes my Google Calendar → Pia speaks the result
> back to me out loud.

Two capabilities, shipped together because they are not separable:
1. **Talkback** — voice in (speech-to-text), voice out (text-to-speech). The conversational loop.
2. **Calendar agent** — read my Google Calendar; create/move/cancel events behind an
   "ask-first" confirmation step.

Nothing else in Milestone 1. No other agents. No multi-model routing yet (one model
hardcoded). No autonomous mode yet (ask-first only). See `04_BUILD_ORDER.md`.

## Hard rules

- **Build the loop before the brains.** Get voice→text→model→voice→speak working with a
  hardcoded model and a stub calendar before touching real OAuth. Prove the pipe, then
  fill it.
- **One agent only.** Calendar. If you find yourself scaffolding a "comms agent" or
  "tasks agent," stop — that is the failure mode that killed earlier attempts.
- **Ask-first for any write.** Pia never creates/moves/deletes a calendar event without
  showing me the proposed change and getting a yes. Reads can be silent.
- **Respect the existing stack.** This is a vanilla-JS frontend plus the existing FastAPI
  backend. Google Cloud is the deployment target: Firebase Hosting for frontend, Cloud Run
  for the containerized FastAPI backend. Don't rewrite the backend into another framework.
- **Secrets via environment variables only.** Never hardcode API keys or OAuth secrets.
  Use Cloud Run/Firebase environment configuration; document every var needed in
  `05_ENV_AND_SETUP.md`.

## What I (the human) will do, and what you do

I handle: buying/configuring domains, Google Cloud OAuth consent screen + credentials,
Cloud Run/Firebase env vars, testing on my own Gmail/Calendar, final deploy clicks.

You handle: all code, the voice loop, the FastAPI backend, the model prompt, the
calendar integration logic, the ask-first confirmation UI, and wiring the orb states to
real conversation state.

## Definition of done for Milestone 1

- [ ] I open the app, tap the orb, and it starts listening (orb enters "speaking/listening" state).
- [ ] My speech is transcribed accurately.
- [ ] Pia replies in voice (TTS) and the orb animates while she speaks.
- [ ] I can say "what's on my calendar tomorrow?" and she reads it back correctly.
- [ ] I can say "move my 3pm to 4:30" and she proposes the change, I confirm, it happens
      in Google Calendar.
- [ ] No secrets in the repo. All config documented.

When Milestone 1 is done and working on me, we talk about Milestone 2 — and only then.

Start by reading the other docs, then propose a concrete file-by-file implementation plan
for Milestone 1 and wait for my go-ahead before writing code.
