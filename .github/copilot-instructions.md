# Copilot workspace instructions — Pia

You are the coding co-pilot for **Pia**, a voice-first personal AI chief-of-staff
("Chief of Agents for People"). Before doing anything in this workspace, read every file in
`/docs` (start with `/docs/README.md`). Those files are the source of truth for vision,
architecture, design, build order, deployment, and the repo-cleanup plan. The full
marching orders are in `/docs/00_GRAND_PROMPT.md`.

## Non-negotiables

1. **Build only the current milestone.** That is **Milestone 1**: voice talkback + Google
   Calendar, working on the founder. tap orb → speech-to-text → one model → calendar
   read/write (ask-first) → text-to-speech → orb animates. Nothing else. The detailed
   scope and "definition of done" are in `/docs/00_GRAND_PROMPT.md` and
   `/docs/04_BUILD_ORDER.md`.
2. **Do not build the orchestrator / agent registry / planner yet.** One agent (calendar)
   is an `if` statement, not a router. The orchestrator is Milestone 3. This is the single
   mistake that has killed this project four times — see `/docs/04_BUILD_ORDER.md` and
   `/docs/06_HISTORY_AND_DECISIONS.md`.
3. **Base repo = the existing code (`pia-ai-main` lineage).** Reuse the working FastAPI
   backend and providers. Remove the avatar UI, add the orb + calendar. Do NOT rewrite
   working code or migrate platforms. See `/docs/08_REPO_CLEANUP.md` and
   `/docs/07_DEPLOYMENT.md`.
4. **One model hardcoded for now**, behind a `chooseModel()` seam. The `llm.py` provider
   already switches claude↔gpt4o — leave that; don't build the full router. See
   `/docs/02_ARCHITECTURE.md`.
5. **Ask-first for every calendar write.** Reads silent; writes go propose → confirm →
   execute. Never write directly.
6. **Secrets via env vars only.** Never commit `.env`. Keep `.gitignore` covering it. See
   `/docs/05_ENV_AND_SETUP.md`.

## Identity / UI

Pia's face is a **holographic, audio-reactive orb** (canvas, 4 states), NOT an avatar and
NOT a 2D circle. Mobile-first, voice-first: mic is the hero, keyboard is a faint fallback.
Full spec in `/docs/03_DESIGN_SPEC.md`.

## How to start

Read `/docs`, confirm the base repo, then produce a **file-by-file plan** (keep / remove /
add) for Milestone 1 and **wait for the founder's go-ahead before writing code**. Then
build in this order: orb frontend wired to the existing voice endpoints → calendar read →
calendar write behind ask-first.

## What the human does (not you)

Domains, Google Cloud OAuth setup, Cloud Run/Firebase env vars, testing on real
Gmail/Calendar, deploy. You do all the code.
