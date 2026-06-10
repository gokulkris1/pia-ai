# Pia — Docs

Context package for building **Pia**, a voice-first personal AI chief-of-staff that
orchestrates a personal ecosystem of agents. Read in order:

1. **00_GRAND_PROMPT.md** — marching orders for the current milestone.
2. **01_VISION.md** — what Pia is and why, the platform/ecosystem bet, the moat.
3. **02_ARCHITECTURE.md** — brain-switching and per-agent autonomy.
4. **03_DESIGN_SPEC.md** — orb identity and mobile home-screen layout.
5. **04_BUILD_ORDER.md** — milestone sequence and anti-scope-creep rules.
6. **05_ENV_AND_SETUP.md** — GCP stack, env vars, and setup.
7. **06_HISTORY_AND_DECISIONS.md** — decision log for continuity.
8. **07_DEPLOYMENT.md** — Cloud Run + Firebase Hosting deployment decision.
9. **08_REPO_CLEANUP.md** — transforming the working base repo into the Milestone 1 spine.

Also included: **`.github/copilot-instructions.md`** — VS Code Copilot auto-loads this as
workspace instructions.

## TL;DR

- **Now (Milestone 1):** voice talkback + Google Calendar, working on the founder. Tap orb
  → talk → Pia reads/writes the calendar (ask-first) → speaks back. One model hardcoded.
  One agent only.
- **The cardinal rule:** never build beyond the current milestone. Earlier attempts died
  from scope creep, not lack of vision.
- **Stack:** Firebase Hosting + Cloud Run container running the existing FastAPI backend.
  Reuse the working `pia-ai-main` lineage; do not start clean.
- **Identity:** a holographic, audio-reactive orb — not an avatar, not a 2D circle.
