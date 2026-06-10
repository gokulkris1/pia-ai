# Pia — Repo Cleanup: forking pia-ai-main into the spine

The base repo is **`pia-ai-main`** — the only one of the old four with real working code.
The other two uploads (`pia44-main`, `pia-main`) are empty skeletons; ignore them. This doc
is the surgical plan: what to keep, what to remove, what to add, so the working "AI twin"
becomes the Milestone-1 Pia spine without rewriting the parts that already work.

## What's already there and WORKS (keep, do not rewrite)

- `backend/main.py` (FastAPI) — already exposes the M1 endpoints:
  `/api/transcribe`, `/api/chat`, `/api/speak`, `/api/call/start`, `/api/call/end`,
  `/api/health`.
- `backend/providers/llm.py` — **already switches `claude` ↔ `gpt4o` with automatic
  fallback** (the seed of brain-switching; the `chooseModel()` seam already half-exists
  here via the `engine` arg + `LLM_ENGINE`).
- `backend/providers/stt.py`, `backend/providers/tts.py` — speech in/out (ElevenLabs TTS
  wired).
- `backend/memory/manager.py`, `backend/persona/` — memory + persona scaffolding (useful
  later; harmless now).
- `.env.example`, `package.json`, `manifest.json` — app config.
- `Dockerfile`, `firebase.json` — GCP deployment config.

## What to REMOVE (the avatar — explicitly deferred)

The repo is the old realistic-avatar "twin." The orb replaces all of it. Delete:

- `frontend/avatar.js`
- `frontend/avatar-realistic.js`
- `frontend/avatar-animator.js`
- `frontend/avatar-intelligent.js`
- `backend/avatar/` (config.py etc.) — and the `/api/avatar/config` route in `main.py`
- avatar references in `frontend/app.js`, `frontend/index.html`, `frontend/style.css`
- `users/default/avatar.json`, `frontend` onboarding photo/avatar bits if not needed for M1

Keep onboarding only if it's the fastest way to capture the founder's profile; otherwise
defer `onboard.html`/`onboard.js` too. M1 is founder-only and can hardcode the profile.

## What to ADD (the genuinely new code)

1. **Orb frontend** — replace the avatar UI with the holographic orb home screen from
   `03_DESIGN_SPEC.md` (canvas orb, 4 states, audio-reactive; flex-column layout; mic-hero
   dock with ghost keyboard). Wire orb state to conversation state (idle/thinking/speaking).
2. **Calendar agent (backend)** — new FastAPI routes, e.g.:
   - `GET  /api/calendar/auth`      → start Google OAuth
   - `GET  /api/calendar/callback`  → OAuth callback, store token
   - `GET  /api/calendar/read`      → read events (silent)
   - `POST /api/calendar/propose`   → return a proposed change (ask-first; no write yet)
   - `POST /api/calendar/confirm`   → execute the confirmed write
   Use Google's Python client. Token storage can reuse the memory/user store pattern.
3. **Intent → calendar wiring** — in `/api/chat`, detect calendar intent and call the
   calendar agent. For M1 a simple intent check is fine; do NOT build a general
   orchestrator/router yet (that's Milestone 3 — see `04_BUILD_ORDER.md`).
4. **Ask-first gate** — any calendar write goes propose → user confirms (voice or tap) →
   confirm. Never write directly.

## Leave clean seams for later (don't build the thing, just the seam)

- `chooseModel(task)` — for now returns the `LLM_ENGINE` constant; `llm.py` already
  supports the switch, so this is nearly free.
- per-agent autonomy setting — store a single value (`calendar: "ask_first"`) even though
  only one agent exists.
- agent registry — NOT now. One agent = an `if`. The registry earns its place at agent 3–4.

## Housekeeping

- Ensure `.gitignore` covers `.env` (the repo has `.env.example` — verify real `.env` is
  ignored).
- Update `.env.example` to the M1 var set (LLM key(s), STT/TTS keys, Google OAuth client
  id/secret/redirect, app base url). See `05_ENV_AND_SETUP.md`.
- Update `README.md` to the Pia chief-of-agents framing and point to `/docs`.

## Sanity check before writing code

The coding agent should: read all `/docs/*.md` → confirm `pia-ai-main` as base → produce a
file-by-file diff plan (keep/remove/add) for Milestone 1 → wait for go-ahead. Build order:
orb frontend wired to existing voice endpoints first (prove the loop on the new UI), then
calendar read, then calendar write behind ask-first.
