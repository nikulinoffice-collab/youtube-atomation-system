# M6.0 Edge Full Frozen-Corpus Runtime Evidence

Status: PASS

This record preserves durable runtime evidence for the shadow-only Edge full frozen-corpus benchmark. It does not certify a preferred M6 engine and does not change production voice behavior.

## Repository binding

- Branch: `factory-v1-voice-m6`
- Benchmark commit: `2f252baa39c16c108a87fbc15e7b3028bd1a29bf`
- Workflow: `M6 Edge Full Corpus One Shot`
- Actions run: `35441422666`
- Job: `105892743501`
- Conclusion: `success`
- Runtime: Ubuntu 24.04, Python 3.11.16
- Edge package: `edge-tts==7.2.7`
- Voice: `en-US-GuyNeural`
- Rate: `+0%`
- Bound audio: PCM S16LE WAV, 24 kHz, mono

## Frozen corpus result

The manifest verification passed with `verified_cases=12`. All 12 frozen cases synthesized successfully and all 12 cryptographically bound records passed validation. The first case was classified cold and the remaining cases warm.

| Case | Synth s | Audio s | RTF | State |
| --- | ---: | ---: | ---: | --- |
| hook | 0.670593 | 4.272 | 0.156974 | cold |
| question | 0.802707 | 3.840 | 0.209038 | warm |
| contrast | 0.746917 | 4.968 | 0.150346 | warm |
| important_fact | 0.761205 | 4.104 | 0.185479 | warm |
| reveal | 0.762402 | 3.408 | 0.223709 | warm |
| neutral | 0.811586 | 5.232 | 0.155120 | warm |
| numbers_dates | 1.360859 | 7.608 | 0.178872 | warm |
| acronyms | 0.816979 | 5.544 | 0.147363 | warm |
| versions_units | 1.013219 | 5.832 | 0.173734 | warm |
| long_sentence | 0.957133 | 11.760 | 0.081389 | warm |
| paragraphs | 0.959754 | 11.304 | 0.084904 | warm |
| short_30s | 1.598717 | 24.696 | 0.064736 | warm |

Validator result: `BOUND_RECORDS=PASS count=12`.

## Artifact evidence

- Artifact ID: `10583164523`
- Name: `m6-edge-full-corpus-2f252baa39c16c108a87fbc15e7b3028bd1a29bf`
- Files uploaded: 37
- ZIP size: 3,631,474 bytes
- Artifact SHA-256: `6f87d4e6b328556e458f8de651b09bb5d34fea7e16fc9074d1aca40b9ce6f4e0`
- Created: 2026-09-19T11:56:14Z
- Retention configured: 7 days

The artifact contains the generated audio, per-case bound records, and summary produced by the one-shot run. Per-case records assert `production_changed=false`.

## Safety / scope

- Production Edge behavior changed: NO.
- M5 baseline changed: NO.
- `main` changed: NO.
- Paid API or paid fallback used: NO.
- Billing enabled or modified: NO.
- Secrets read, printed, rotated, or modified: NO.
- Publishing/upload agent invoked: NO.
- This evidence does not select an M6.0 winner and does not satisfy the M6.0 human review gate by itself.
