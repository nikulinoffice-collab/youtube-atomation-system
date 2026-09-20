# M6.0 Human Review — Robotic Voice Finding

Date: 2026-09-20
Status: QUALITY_TARGET_NOT_MET / M6.0_REOPENED

Human listening found a clear improvement in intonation, but the retained male voice still sounds emotionally detached, synthetic and robotic. This is a quality failure for the M6 objective, not a runtime failure.

## Consequence

- Do not approve M6.0 -> M6.1.
- Do not attempt to hide the defect with mastering/DSP.
- Keep the existing prosody/direction work as useful evidence.
- Reopen M6.0 candidate research with a stricter target: human-likeness and voice identity/timbre quality first, while retaining controllable pacing/prosody.
- Male voice only for the next human listening set.
- Production Edge remains unchanged.

## 2026 candidate screen

Candidates are screened fail-closed for zero-cost commercial suitability before runtime work.

| Candidate | Human-likeness / expressive relevance | License gate | M6 disposition |
| --- | --- | --- | --- |
| Qwen3-TTS | 2026 official open-source TTS family; supports voice cloning/custom voice paths and is a strong candidate for modern neural voice identity/prosody testing | Official repository code is Apache-2.0. Exact checkpoint and selected male voice/reference asset rights still require four-part verification before production certification | QUALIFY_FOR_TECHNICAL_PROBE |
| IndexTTS-2.5 | Official materials describe fine-grained emotion, speed and pronunciation control and zero-shot voice cloning | Bilibili Model Use License; commercial terms/thresholds and selected reference-voice rights require exact audit | LICENSE_AUDIT_BEFORE_RUNTIME |
| CosyVoice3 | Official project recommends Fun-CosyVoice3-0.5B and provides zero-shot/instruct generation paths | Exact model/checkpoint and selected reference-voice rights must be audited before production qualification | LICENSE_AUDIT_BEFORE_RUNTIME |
| F5-TTS | Strong zero-shot natural speech candidate | Official pretrained models are CC-BY-NC because of Emilia training data | DISQUALIFIED_ZERO_COST_COMMERCIAL |
| Fish Speech / Fish Audio S2 | Modern expressive TTS candidate | 2026 Fish Audio Research License requires a separate license for commercial use | DISQUALIFIED_ZERO_COST_COMMERCIAL |

The next technical probe must not use a celebrity/public-figure voice. It must use either an upstream voice asset whose commercial rights are explicitly established or a Factory-owned/explicitly licensed adult male reference. If neither is available, the probe may establish model runtime only but cannot create a production-qualified voice candidate.

## Acceptance focus for the next blind set

A candidate must be judged specifically on: absence of robotic timbre, natural micro-prosody, phrase-to-phrase continuity, believable emphasis, non-uniform pitch/energy, natural consonant/vowel transitions, sensible breath-like phrasing without artificial breath insertion, stable pronunciation, and restrained emotion. Runtime speed is secondary to human-likeness at this stage.

No winner is selected by this document.
