# M6.0 TTS Engine Qualification Matrix

Status: IN_PROGRESS. This document is evidence-first: unknown fields remain UNKNOWN until verified or measured. Production Edge path is unchanged.

## Required dimensions

| # | Dimension | Edge legacy | Gemini TTS | Chatterbox-Nano | MOSS-TTS-Nano | Kokoro |
|---|---|---|---|---|---|---|
|1|Naturalness|BENCHMARK|TBD|TBD|TBD|TBD|
|2|English quality|BENCHMARK|TBD|TBD|TBD|TBD|
|3|Intonation|TBD|TBD|TBD|TBD|TBD|
|4|Emotionality|TBD|TBD|TBD|TBD|TBD|
|5|Speed control|TBD|TBD|TBD|TBD|TBD|
|6|Pause control|TBD|TBD|TBD|TBD|TBD|
|7|Pitch/prosody|TBD|TBD|TBD|TBD|TBD|
|8|SSML/equivalent|TBD|TBD|TBD|TBD|TBD|
|9|Pronunciation stability|MEASURE|MEASURE|MEASURE|MEASURE|MEASURE|
|10|Word/sentence timestamps|TBD|TBD|TBD|TBD|TBD|
|11|Python automation|YES-current|TBD|TBD|YES-repo CLI|TBD|
|12|GitHub Actions fit|YES-current|TBD|TBD|LIKELY-CPU|TBD|
|13|GPU required|NO-current|NO-client|TBD|NO (repo states 4-core CPU streaming)|TBD|
|14|Generation speed|MEASURE|MEASURE|MEASURE|MEASURE|MEASURE|
|15|Free-use limits|current baseline|VERIFY CURRENT|local model|local model|local model|
|16|YouTube/TikTok license|VERIFY TERMS|VERIFY TERMS|VERIFY WEIGHTS|Apache-2.0 family evidence; verify Nano root LICENSE|Apache-2.0 weights evidence|
|17|Commercial output|VERIFY|VERIFY|VERIFY|VERIFY|Apache-2.0 weights evidence|
|18|Model quality/size|service|service|TBD|~0.1B params|~82M params|
|19|Integration complexity|MEASURE|MEASURE|MEASURE|MEASURE|MEASURE|
|20|Availability risk|service dependency|preview/free-tier dependency|local/upstream dependency|local/upstream dependency|local/upstream dependency|

## Evidence captured 2026-09-15

- Gemini 2.5 Flash Preview TTS pricing documentation exposes a free tier, but explicitly labels the TTS model preview and notes preview models can change and have stricter rate limits. This is not yet sufficient to certify commercial-output terms or long-term availability.
- OpenMOSS/MOSS-TTS-Nano describes a 0.1B multilingual model, streaming inference, 48 kHz stereo output and CPU-friendly operation on a 4-core CPU. Its README says licensing follows the root LICENSE; the broader MOSS-TTS family states Apache-2.0. Nano remains provisional until the exact root LICENSE/model-weight terms are inspected directly.
- Kokoro-82M evidence identifies ~82M parameters and Apache-2.0 model weights, supporting local deployment and commercial use under that license; exact selected wrapper dependencies must still be audited separately.
- Chatterbox search evidence describes MIT-licensed code and emotion exaggeration control, but this matrix deliberately does not certify Chatterbox-Nano weights/commercial status until the exact Nano repository/model card is verified.

## Measurement contract

All engines must synthesize the exact same benchmark corpus. Record cold-start time, synthesis time, output duration, realtime factor (generation_seconds/audio_seconds), peak RAM where measurable, artifact size, failure/retry count, and whether GPU was used. Listening samples must be randomized to opaque IDs before human scoring.

No engine may become production-selected during M6.0. M6.0 ends at HUMAN_REVIEW_REQUIRED after the technical matrix and blind sample package are complete.
