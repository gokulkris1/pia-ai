# Pia — Interface & Design Spec

## Platform

Mobile-first (and mobile-only for now). The long-term intent is omnipresence across phone,
watch, car, audio, and AR, which is why the identity is an orb — it scales to any surface
and size. Keep the orb resolution- and size-agnostic.

## Identity: the orb (not an avatar)

Pia's face is a **holographic, volumetric orb** — NOT a 2D circle and NOT a human/clone
avatar. The avatar/clone idea is explicitly deferred to a much later phase (when Pia knows
the user well enough to speak for them); building a face now is a scope trap.

### What the orb looks like (the agreed direction)

A sphere of light points rotating in real 3D space, rendered on an HTML canvas:
- Points are distributed on a sphere (Fibonacci distribution for even coverage).
- The sphere rotates slowly; each point gets **brighter as it rotates toward the viewer
  and dimmer as it falls behind**, so the viewer reads genuine depth and volume.
- **Additive blending** ("lighter" composite op) so it glows like a projection rather than
  sitting flat like a graphic.
- A soft central light bloom. Optional faint scanline flicker for the "projected light"
  feel.
- No decorative rings/particles/chromatic-aberration clutter. The future-design principle
  here is *less, with depth and light doing the work* — not more effects. Restraint reads
  as advanced; busyness reads as dated.
- No literal "p" monogram or elementary labels on the orb.

### Orb states (each its own color + energy)

- **idle** — calm, slow breathe, cool tone. This matters most for an "always there"
  presence. Color: cool blue/cyan family.
- **thinking** — tighter, faster, working. Purple family.
- **speaking** — bright, energetic, expands/reacts. Bright cyan/white.
- **alert** — needs attention. Amber family.

The orb is **audio-reactive**: it responds to real microphone input (Web Audio API
analyser) when the user speaks, and to Pia's TTS output when she speaks.

## Home screen layout (agreed)

Built as a **flex column** (not absolute positioning — that caused overlap bugs). Six
stacked bands, each with its own fixed spacing so nothing collides at any screen height:

1. **Top bar** — menu (left), `pia` wordmark (center, lowercase, letter-spaced), history
   (right). Safe padding below the notch.
2. **Mode chips** — small pills: model routing state ("auto"), per-agent autonomy
   ("ask first"), agents count ("N agents"). Own band, breathing room above/below.
3. **Orb** — flex-grows to fill the remaining middle space; always centered.
4. **Status block** — grouped together: status line ("tap to speak"), subline
   ("pia is listening for you"), and the quiet **model pill** ("opus · auto-routing").
5. **Dock** — the **mic is the single hero action**: one large glowing circular button,
   centered. Voice is primary. The **keyboard is a small faint "ghost" icon** to the side
   — present but clearly secondary. (Optional plus icon on the other side for
   attachments/quick actions.) Tapping the keyboard slides up a text field only for that
   moment, then collapses back to voice.
6. **Home indicator** — clean bottom margin.

### Voice-first principle

Pia is voice-first. Text must always be available but must never take center stage. A full
text input bar with a "type here" placeholder is wrong — it fights the voice-first intent.
Chat is the fallback, not the default invitation.

## Aesthetic reference

We are matching the *structure* of Microsoft Copilot's mobile app (top nav, clean center,
prompt dock at the bottom) but **inverting the emphasis**: Copilot (post May 2026
redesign) is minimal, monochrome, text-forward with a small voice visualizer. Pia makes
the visualizer (the orb) the entire stage, with chat as the quiet fallback. Same restraint,
opposite emphasis. Dark background throughout.

## Open UX decisions (decide during build, not blockers)

- Mic: tap-to-talk vs. always-listening wake word.
- Whether tapping the orb itself (not just the mic) starts a conversation.
