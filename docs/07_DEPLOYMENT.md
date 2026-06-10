# Pia — Deployment Decision: GCP-only for Milestone 1

## Decision

Milestone 1 deploys on Google Cloud only:

- **Frontend:** Firebase Hosting serves the static `frontend/` app.
- **Backend:** Cloud Run runs the existing FastAPI app from a container.

Do not rewrite the FastAPI backend into serverless functions. The backend already has the
working voice loop endpoints (`/api/transcribe`, `/api/chat`, `/api/speak`,
`/api/call/start`, `/api/call/end`), so M1 keeps that code and containers it for Cloud Run.

## Repo reality

- `Dockerfile` builds the existing FastAPI backend and copies `frontend/`, `users/`, and
  `persona/` into the image for local/same-origin serving.
- `firebase.json` hosts `frontend/` as the Firebase static app.
- `.github/workflows/deploy.yml` is intentionally disabled except for a manual no-op;
  it no longer deploys to Netlify.
- `netlify.toml` and `render.yaml` are removed.

## Runtime URLs

Use the real deployed URLs once Cloud Run and Firebase are created:

```text
PIA_API_BASE=https://pia-backend-REPLACE_WITH_CLOUD_RUN_URL.a.run.app
APP_BASE_URL=https://pia-ai-REPLACE_WITH_FIREBASE_SITE.web.app
GOOGLE_OAUTH_REDIRECT_URI=https://pia-backend-REPLACE_WITH_CLOUD_RUN_URL.a.run.app/api/calendar/callback
```

The frontend reads `window.PIA_API_BASE` from `frontend/config.js`. For local FastAPI dev it
uses same-origin (`''`). For hosted Firebase, replace the Cloud Run placeholder with the
actual Cloud Run service URL.

## Manual M1 deploy shape

Backend:

```bash
gcloud run deploy pia-backend \
  --source . \
  --region REPLACE_WITH_REGION \
  --allow-unauthenticated \
  --set-env-vars LLM_ENGINE=claude,PIA_USER_ID=default,GOOGLE_OAUTH_REDIRECT_URI=https://pia-backend-REPLACE_WITH_CLOUD_RUN_URL.a.run.app/api/calendar/callback
```

Set secrets such as `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, and Google OAuth
credentials as Cloud Run environment variables or Secret Manager-backed env vars. Never
commit real secrets.

Calendar read uses OAuth token storage. Locally, the token is written to the ignored file
`users/default/google_calendar_token.json`. On Cloud Run, use `GOOGLE_CALENDAR_TOKEN_JSON`
or Secret Manager-backed env vars after the first OAuth connection; otherwise the token may
only live for the lifetime of a container instance.

Frontend:

```bash
firebase deploy --only hosting
```

## When to revisit

After M1 works on the founder's real calendar, revisit automation and environment
promotion. Until then, manual deploy is acceptable and lower-risk than introducing a new
CI/CD surface.
