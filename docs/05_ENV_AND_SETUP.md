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
ANTHROPIC_API_KEY=
LLM_ENGINE=claude

# STT: Whisper via OpenAI
OPENAI_API_KEY=

# TTS: ElevenLabs
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=

# Google Calendar OAuth
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=https://pia-backend-REPLACE_WITH_CLOUD_RUN_URL.a.run.app/api/calendar/callback
GOOGLE_CALENDAR_TOKEN_JSON=      # optional token JSON for deployed Cloud Run
GOOGLE_CALENDAR_TOKEN_PATH=      # optional local token file path override
PIA_TIMEZONE=Europe/Dublin

# App
APP_BASE_URL=https://pia-ai-REPLACE_WITH_FIREBASE_SITE.web.app
PIA_API_BASE=https://pia-backend-REPLACE_WITH_CLOUD_RUN_URL.a.run.app
PIA_USER_ID=default
```

Never commit real secrets. Local `.env` is ignored; Cloud Run should receive production
secrets via env vars or Secret Manager-backed env vars.

For local OAuth testing, the callback stores the token at
`users/default/google_calendar_token.json`, which is ignored by git. For Cloud Run, prefer
setting `GOOGLE_CALENDAR_TOKEN_JSON` or Secret Manager-backed env vars after the first OAuth
connection so token persistence does not depend on container filesystem lifetime.

Calendar writes require the Google scope `https://www.googleapis.com/auth/calendar.events`.
If a token was created during the read-only step, delete the local token or revisit
`/api/calendar/auth` and approve the expanded access before testing create/move/cancel.

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
