# Pia — Stack, Environment & Setup

## Current stack

- **Frontend:** vanilla JS + HTML, hosted on Firebase Hosting.
- **Backend:** the existing FastAPI app, containerized with `Dockerfile` and deployed to Cloud Run.
- **Voice:** Web Speech API where available, Whisper fallback through `/api/transcribe`, and ElevenLabs through `/api/speak`.
- **LLM:** Claude for Milestone 1 via `LLM_ENGINE=claude`.
- **Calendar:** Google Calendar API via OAuth routes added in the backend during M1 Step 2/3.

Do not rewrite the FastAPI backend. Keep the working voice endpoints and add calendar routes
beside them.

## What the human sets up

1. Enable Google Calendar API in Google Cloud.
2. Configure OAuth consent screen with the founder as a test user for M1.
3. Create OAuth Client ID credentials and record client ID + secret.
4. Add runtime variables/secrets to Cloud Run and Firebase config as needed.
5. Test against the founder's real Google Calendar.
6. Do final deploy clicks or manual deploy commands.

## Environment variables needed (Milestone 1)

```text
# LLM: Claude hardcoded for M1
calude_key=
LLM_ENGINE=claude

# STT: Whisper via OpenAI
OpenAI_Key=

# TTS: ElevenLabs
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=

# Google Calendar OAuth
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=https://pia-backend-REPLACE_WITH_CLOUD_RUN_URL.a.run.app/api/calendar/callback

# App
APP_BASE_URL=https://pia-ai-REPLACE_WITH_FIREBASE_SITE.web.app
PIA_API_BASE=https://pia-backend-REPLACE_WITH_CLOUD_RUN_URL.a.run.app
PIA_USER_ID=default
```

Never commit real secrets. Local `.env` is ignored; Cloud Run should receive production
secrets via env vars or Secret Manager-backed env vars.

## Repo layout

```text
frontend/            static Firebase Hosting app: index, orb canvas, dock
backend/             FastAPI backend: STT, chat, TTS, call session, calendar routes
Dockerfile           Cloud Run container for the existing FastAPI backend
firebase.json        Firebase Hosting config
.github/workflows/   deploy workflow disabled for M1; manual GCP deploy only
docs/                product, architecture, design, build order, setup, deployment
```

## First task order

Build in order: orb frontend wired to existing voice endpoints, then real calendar read,
then calendar write behind ask-first confirmation.
