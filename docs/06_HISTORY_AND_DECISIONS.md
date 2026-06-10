# Pia — History & Decision Log

A running record so any coding agent (or future-you) has the full context without
re-deriving it. Newest decisions at the bottom.

## Background

- The Pia idea originated in 2024 as a presence-aware personal AI ("AI twin").
- It has been built and abandoned several times across multiple repos. The furthest-along
  earlier repo had a modular structure (skills/, voice/, config/, main.py — a voice-first
  Python assistant). Other repos were empty restarts.
- **Root cause of every abandonment:** no forcing function and scope creep — rebuilding
  the skeleton repeatedly instead of pushing one slice to a working demo. This is the
  single most important lesson. See `04_BUILD_ORDER.md`.
- A Netlify deploy exists (vanilla JS voice/video "AI twin" call UI).

## Key decisions (the pivot that matters)

1. **From "AI twin" → "AI chief-of-staff" → "agent orchestrator."** Pia is not one
   assistant; she is the orchestration layer that manages a personal ecosystem of
   specialized agents (calendar, comms, tasks, finance, health, projects, bookings, and
   eventually third-party agents like a photo editor, nutrition, shopping, hairstylist).
   The user only ever talks to Pia. (See `01_VISION.md`.)

2. **Founder is user zero.** Build for the founder's own life first — accounts, diary,
   personal stuff, projects, health, year-long to-dos, bookings — before generalizing.

3. **"Be excellent at one paid thing first."** The "super assistant" is the roadmap, not
   the launch. Resisting the urge to build everything at once is the whole discipline.

4. **Identity = orb, not avatar.** Considered a clone/avatar; explicitly deferred. The orb
   is holographic/volumetric (3D rotating light-point sphere, additive glow, depth via
   brightness). Rejected: 2D flat orb; busy "2050" version with rings/particles/chromatic
   aberration (too cluttered — future = restraint, depth, light). Removed the "p" monogram.
   (See `03_DESIGN_SPEC.md`.)

5. **Two independent control axes.** Brain-switching (auto model routing, Copilot-auto
   style, user can override / compare / pin) and autonomy modes (read-only / ask-first /
   autonomous, **per-agent**, Copilot-permission style). They are separate axes. (See
   `02_ARCHITECTURE.md`.)

6. **Mobile-first, omnipresence later.** Phone now; watch/car/audio/AR on the horizon. The
   orb was chosen partly because it scales across all surfaces.

7. **UI matches Copilot's structure, inverts its emphasis.** Copilot's May 2026 redesign
   went minimal/monochrome/text-forward with a small voice viz. Pia makes the orb the whole
   stage and keeps chat as a quiet fallback. Home screen is a flex column of six bands
   (top bar / chips / orb / status block / dock / home indicator) — flex, not absolute, to
   avoid overlap. Mic is the hero; keyboard is a faint ghost icon.

8. **First slice = talkback + calendar, together.** Chosen as the smallest thing that is
   genuinely Pia. Calendar picked as agent #1 (most contained API, most demoable, most
   intuitive autonomy story). Runs ask-first in M1.

9. **Positioning sharpened: "Chief of Agents for People."** Pia is not an agent; she is the
   Chief Agent — the layer above all other agents that knows you, picks the right brain,
   calls the right tool, uses the right device, and coordinates quietly. Brand line:
   "Another You. Everywhere." This is north-star framing; it does NOT change the build
   order. The orchestrator that realizes this hierarchy is Milestone 3, not now.

10. **Base repo chosen: `pia-ai-main`.** Of the four old attempts, three uploads were
    inspected: `pia44-main` (~53 lines, empty skeleton), `pia-main` (empty, 0-line
    main.py), and `pia-ai-main` (~876 lines of real, working code). Decision: **fork
    `pia-ai-main`, strip the avatar, add the orb + calendar.** It already has the M1
    endpoints (`/api/transcribe`, `/api/chat`, `/api/speak`) and an LLM provider that
    switches claude↔gpt4o with fallback. Do not start clean; do not rewrite working code.
    (See `08_REPO_CLEANUP.md`.)

11. **Deployment: GCP-only for M1.** Reuse the working FastAPI backend by containerizing it
   for Cloud Run. Host the static frontend on Firebase Hosting. Do not rewrite the backend
   into another framework. (See `07_DEPLOYMENT.md`.)

12. **Conversation/session naming.** The inherited `/api/call/start`, `/api/call/end`, and
   `session/call.py` machinery now represent conversation state, not a twin-era phone-call
   UI. Keep the names through M1 because the flow works and renaming would add risk before
   calendar. Rename to agent-neutral conversation/session naming after the calendar read/write
   spine is working.

## Working agreement

- Human does: domains, Google Cloud OAuth, Cloud Run/Firebase env vars, testing on real
  Gmail/Calendar, deploy clicks.
- Coding agent does: all code, voice loop, FastAPI backend, model prompt, calendar logic,
  ask-first confirmation, wiring orb states to conversation state.

## Status

- [x] Vision, architecture, design spec, build order agreed.
- [x] Orb visual direction locked (holographic, volumetric, audio-reactive, 4 states).
- [x] Home screen layout locked (flex column, mic-hero dock, ghost keyboard).
- [x] Orb + voice spine implemented: the avatar/camera/restaurant paths are removed, the orb UI is wired to `/api/call/start`, `/api/chat`, and `/api/speak`, and the FastAPI app boots locally.
- [ ] Voice round-trip with real STT/LLM/TTS keys — pending first browser test with valid environment variables.
- [x] Calendar read code implemented: Google OAuth start/callback, ignored local token storage, `/api/calendar/status`, `/api/calendar/read`, and narrow `/api/chat` read intent are wired.
- [x] Calendar read OAuth/browser validation — local and deployed `hellopia` Cloud Run reads are verified against the founder's Google Calendar.
- [ ] Calendar write — next Milestone 1 step; writes remain ask-first.

## Next action

Run the first voice-loop + calendar-read test with real keys and Google OAuth credentials,
then build calendar-write (ask-first).
