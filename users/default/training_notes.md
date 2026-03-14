# PIA Training Notes — Gokul / default

Free-form notes about what the twin gets right, what needs improving,
and observations to feed into future training sessions.

---

## Format

Add dated entries. Be specific — vague notes don't help the training system.

```
## YYYY-MM-DD
### What worked
### What missed
### Suggested fix
```

---

## 2026-03-14 — Initial setup

### What worked
- Persona file created from scratch, structure solid

### What missed
- Cloned voice not yet active — using Rachel default
- Humor calibration untested
- Response pacing not yet measured against real call behaviour

### Suggested fix
- Record 5-min audio of yourself speaking naturally, clone voice in ElevenLabs
- Do 3–5 real test calls, then come back and update `persona.json`:
  - `typical_phrases` — add real phrases you catch yourself using
  - `speaking_style.pacing` — adjust based on how rushed/slow PIA feels
  - `humor.style` — refine after hearing a few responses

---

## Training signal ideas (future)

When the training pipeline is built, these signals will feed the system:

- **thumbs up/down** on each PIA response (quick in-call rating)
- **phrase capture** — flag when PIA uses a phrase you'd never say
- **tone mismatch** — flag when tone feels wrong for context
- **length complaints** — flag when responses are too long or short
- **topic gaps** — things PIA didn't know that it should
