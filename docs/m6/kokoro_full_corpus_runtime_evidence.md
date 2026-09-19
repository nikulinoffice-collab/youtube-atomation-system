# M6.0 Kokoro Full Frozen-Corpus Runtime Evidence

Status: PASS (technical benchmark only)

This record preserves durable runtime evidence for the shadow-only Kokoro full frozen-corpus benchmark. It does not certify Kokoro for commercial production and does not select an M6 engine.

## Repository and Actions binding

- Branch: `factory-v1-voice-m6`
- Benchmark commit: `cbc6bddf28c30e82f184dc1b634f92d01577d8e8`
- Workflow: `M6 Kokoro Full Corpus One Shot`
- Actions run: `35450357668`
- Job: `105916323466`
- Conclusion: `success`
- Runtime: Ubuntu 24.04, Python 3.11.16
- Engine: `kokoro==0.9.4`
- Voice: `af_heart`
- Speed: `1.0`
- Execution: CPU-only; CUDA unavailable
- Audio: PCM S16LE WAV, 24 kHz

## Frozen corpus result

Manifest verification passed with `verified_cases=12`. All 12 cases synthesized and all 12 bound records passed.

| Case | Synth s | Audio s | RTF | State |
| --- | ---: | ---: | ---: | --- |
| hook | 2.573875 | 4.250 | 0.605618 | cold |
| question | 2.056364 | 3.650 | 0.563387 | warm |
| contrast | 2.096959 | 3.800 | 0.551831 | warm |
| important_fact | 2.328521 | 4.150 | 0.561089 | warm |
| reveal | 1.661853 | 3.000 | 0.553951 | warm |
| neutral | 2.709995 | 5.050 | 0.536633 | warm |
| numbers_dates | 4.581323 | 8.275 | 0.553634 | warm |
| acronyms | 3.306933 | 6.025 | 0.548869 | warm |
| versions_units | 3.679134 | 6.650 | 0.553253 | warm |
| long_sentence | 7.400069 | 13.450 | 0.550191 | warm |
| paragraphs | 6.007122 | 11.200 | 0.536350 | warm |
| short_30s | 12.202802 | 21.925 | 0.556570 | warm |

Validator: `BOUND_RECORDS=PASS count=12`.

## Artifact

- Artifact ID: `10586710488`
- Name: `m6-kokoro-full-corpus-cbc6bddf28c30e82f184dc1b634f92d01577d8e8`
- Size: 3,243,466 bytes
- SHA-256: `bd66fac1ce5660e01f62b6fc14714ee30f3ae15929e5a9336f09030040716466`
- Retention: 7 days

## Qualification limits

The CPU-only dependency path succeeded and avoided the earlier CUDA runtime footprint. This is runtime evidence only. Licensing remains `TECHNICAL_ONLY / NOT_COMMERCIAL_CERTIFIED_PENDING_EXPLICIT_VOICEPACK_RIGHTS`: model/code licensing does not independently prove commercial rights for the selected `af_heart` voicepack. English G2P/espeak-ng distribution obligations remain a separate compliance item.

Production voice behavior changed: NO. M5/main changed: NO. Paid API/billing/publishing/secrets: NO.
