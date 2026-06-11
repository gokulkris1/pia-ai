window.PIA_API_BASE = window.PIA_API_BASE || '';

// Optional client override for the realtime voice mode ('vapi' | 'classic').
// When left empty, the mode comes from GET /api/voice/config (server env
// PIA_VOICE_MODE, default 'classic'). Set to 'classic' here to force the
// original record→transcribe→chat→speak fallback regardless of server config.
window.PIA_VOICE_MODE = window.PIA_VOICE_MODE || '';
