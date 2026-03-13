# pia

Personal ambient AI assistant. Voice-first, mobile-ready, engine-switchable.

## features
- voice input (Web Speech API) + text-to-speech output
- switchable AI engine: Claude (Anthropic) or GPT-4o (OpenAI)
- skills: weather, reminders, web search, summarizer, notes
- conversation memory
- PWA — install on any phone from the browser

## deploy

Hosted on Netlify. Connect this repo and it auto-deploys on every push.

### environment variables (set in Netlify dashboard)

| variable | description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key (for Claude) |
| `OPENAI_API_KEY` | OpenAI API key (for GPT-4o) |

Users can also enter their own API keys directly in the app settings.

## structure

```
pia-ai/
├── index.html                    # main app (single file)
├── manifest.json                 # PWA manifest
├── netlify.toml                  # Netlify config + headers
└── netlify/
    └── functions/
        └── ai-proxy.mjs          # serverless proxy (bypasses CORS)
```

## local dev

```bash
npm install -g netlify-cli
netlify dev
```
