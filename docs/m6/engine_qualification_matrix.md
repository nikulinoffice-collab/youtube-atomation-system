# M6.0 TTS Engine Qualification Matrix

Status: IN_PROGRESS. This document is evidence-first: unknown fields remain UNKNOWN until verified or measured. Production Edge path is unchanged.

## Required dimensions

| # | Dimension | Edge legacy | Gemini TTS | Chatterbox-Nano | MOSS-TTS-Nano | Kokoro |
|---|---|---|---|---|---|---|
|1|Naturalness|BENCHMARK|TBD|BENCHMARK|TBD|TBD|
|2|English quality|BENCHMARK|TBD|English-only official Nano|20-language model incl. English; BENCHMARK|TBD|
|3|Intonation|TBD|TBD|BENCHMARK|TBD|TBD|
|4|Emotionality|TBD|TBD|Native paralinguistic tags; BENCHMARK quality|TBD|TBD|
|5|Speed control|TBD|TBD|No direct certification yet; benchmark pacing|TBD|TBD|
|6|Pause control|TBD|TBD|Paralinguistic tags are not a substitute for deterministic pause measurement|TBD|TBD|
|7|Pitch/prosody|TBD|TBD|TBD|TBD|TBD|
|8|SSML/equivalent|TBD|TBD|Native paralinguistic tags; no SSML claim certified|TBD|TBD|
|9|Pronunciation stability|MEASURE|MEASURE|MEASURE|MEASURE|MEASURE|
|10|Word/sentence timestamps|TBD|TBD|TBD|TBD|TBD|
|11|Python automation|YES-current|TBD|YES-official Python implementation|YES-direct Python + packaged CLI|TBD|
|12|GitHub Actions fit|YES-current|TBD|LIKELY-CPU; must measure runner RAM/time|LIKELY-CPU; must measure runner RAM/time|TBD|
|13|GPU required|NO-current|NO-client|NO; official Nano targets CPU/on-device|NO; official model card states CPU operation and 4-core streaming|TBD|
|14|Generation speed|MEASURE|MEASURE|Official claim 3x realtime on 8 CPU cores; independently MEASURE|Realtime/streaming claimed; independently MEASURE|MEASURE|
|15|Free-use limits|current baseline|VERIFY CURRENT|local model; no API quota dependency|local model; no API quota dependency|local model|
|16|YouTube/TikTok license|VERIFY TERMS|VERIFY TERMS|Official HF model card declares MIT; exact bundled/reference voice asset provenance still audit|Official HF model card declares Apache-2.0; exact bundled/reference voice asset provenance still audit|Apache-2.0 weights evidence|
|17|Commercial output|VERIFY|VERIFY|PROVISIONAL: official model card/checkpoint is MIT; voice/reference assets and dependency chain still gated|PROVISIONAL: official model card/checkpoint is Apache-2.0; voice/reference assets and dependency chain still gated|PROVISIONAL YES: Apache-2.0 weights; wrapper/dependencies still require audit|
|18|Model quality/size|service|service|110M params official|~0.1B TTS + ~20M tokenizer|~82M params|
|19|Integration complexity|MEASURE|MEASURE|Python/local; reference clip required by official Nano example; MEASURE dependencies/cold start|Python/local + tokenizer + voice prompt; MEASURE dependencies/cold start|MEASURE|
|20|Availability risk|service dependency|preview/free-tier dependency|local model; upstream/download dependency|local/upstream dependency|local/upstream dependency|

## Evidence captured 2026-09-15

- Gemini 2.5 Flash Preview TTS pricing documentation exposes a free tier, but explicitly labels the TTS model preview and notes preview models can change and have stricter rate limits. This is not sufficient to certify commercial-output terms or long-term availability.
- The official Hugging Face model card `OpenMOSS-Team/MOSS-TTS-Nano-100M` currently declares `apache-2.0`, describes the model as ~0.1B parameters, supports 20 languages including English, states that it can run directly on CPU, and states streaming can run on a 4-core CPU. It documents direct Python inference and a packaged CLI. This is stronger evidence than repository-code licensing alone because it is attached to the distributed model card/checkpoint. However, bundled/reference voice prompts, tokenizer artifacts, dependency licenses, and generated-output restrictions still require an asset/dependency audit before commercial production certification.
- The exact `OpenMOSS/MOSS-TTS-Nano` root LICENSE was separately inspected and is Apache License 2.0, including a perpetual worldwide no-charge royalty-free copyright grant subject to Apache conditions. Repository-code license and official HF model-card license are therefore independently captured rather than inferred from one another.
- Kokoro-82M model-card evidence identifies ~82M parameters and Apache-2.0 model weights and explicitly describes production deployment/commercial and non-commercial use. This makes Kokoro a strong local zero-cost candidate. The exact Python wrapper, phonemizer, voice assets and transitive dependencies selected for Factory still require separate audit before certification.
- The official Hugging Face model card `ResembleAI/chatterbox-nano` itself declares `mit`. It identifies Nano as a 110M English model, CPU/on-device oriented, with an official claim of about 3x realtime on 8 CPU cores and native paralinguistic tags. Its documented Python example loads `ChatterboxTurboTTS.from_pretrained(..., nano=True)` and uses a reference audio clip for generation. This closes the exact hosted model-card/checkpoint license ambiguity: both upstream repository and official hosted Nano model card declare MIT. It does not automatically certify any user-supplied or bundled reference voice, third-party conversion, dependency, or downstream generated-output policy.
- Chatterbox-Nano outputs include provenance watermarking according to the vendor's Nano release material. Preserve this behavior; do not use third-party forks whose purpose is watermark removal.

## Licensing gate

For every local candidate, certification requires four separately recorded facts where applicable: (1) repository/code license, (2) model-weight/checkpoint license, (3) voice/model-card or other asset restrictions, and (4) restrictions affecting commercial generated output. A permissive repository license alone is never sufficient evidence for all four.

An official model-card license closes the checkpoint-license evidence only when the card is the authoritative card for the exact model being benchmarked. It does not silently license user-supplied reference voices, separately hosted tokenizers/phonemizers, bundled voice prompts, third-party wrappers/conversions, or training/reference datasets.

## Measurement contract

All engines must synthesize the exact same benchmark corpus. Record cold-start time, synthesis time, output duration, realtime factor (generation_seconds/audio_seconds), peak RAM where measurable, artifact size, failure/retry count, and whether GPU was used. Listening samples must be randomized to opaque IDs before human scoring.

Vendor performance claims are evidence for feasibility only, never substitutes for Factory measurements. CPU speed, RAM, cold-start and RTF must be measured on the actual GitHub Actions benchmark environment before a candidate can pass M6.0.

No engine may become production-selected during M6.0. M6.0 ends at HUMAN_REVIEW_REQUIRED after the technical matrix and blind sample package are complete.
