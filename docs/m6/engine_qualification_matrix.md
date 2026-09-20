# M6.0 TTS Engine Qualification Matrix

Status: M6.0_REOPENED / QUALITY_TARGET_NOT_MET. Human review found improved intonation but persistent robotic/emotionally detached voice quality. PASS/FAIL/UNKNOWN below remains evidence-first. Production Edge path is unchanged.

## Required dimensions

| # | Dimension | Edge legacy | Gemini TTS | Chatterbox-Nano | MOSS-TTS-Nano | Kokoro |
|---|---|---|---|---|---|---|
|1|Naturalness|BENCHMARK|TBD|BENCHMARK|TBD|TBD|
|2|English quality|BENCHMARK|TBD|English-only official Nano|20-language model incl. English; BENCHMARK|English model; BENCHMARK|
|3|Intonation|TBD|TBD|BENCHMARK|TBD|TBD|
|4|Emotionality|TBD|TBD|Native paralinguistic tags; BENCHMARK quality|TBD|TBD|
|5|Speed control|TBD|TBD|No direct certification yet; benchmark pacing|TBD|TBD|
|6|Pause control|TBD|TBD|Paralinguistic tags are not a substitute for deterministic pause measurement|TBD|TBD|
|7|Pitch/prosody|TBD|TBD|TBD|TBD|TBD|
|8|SSML/equivalent|TBD|TBD|Native paralinguistic tags; no SSML claim certified|TBD|TBD|
|9|Pronunciation stability|MEASURE|MEASURE|MEASURE|MEASURE|MEASURE|
|10|Word/sentence timestamps|TBD|TBD|TBD|TBD|TBD|
|11|Python automation|YES-current|TBD|YES-official Python implementation|YES-direct Python + packaged CLI|YES-official pip package/model usage|
|12|GitHub Actions fit|YES-current|TBD|LIKELY-CPU; must measure runner RAM/time|LIKELY-CPU; must measure runner RAM/time|LIKELY-local; must measure runner RAM/time and GPL dependency implications|
|13|GPU required|NO-current|NO-client|NO; official Nano targets CPU/on-device|NO; official model card states CPU operation and 4-core streaming|NO hard GPU requirement established for deployment; MEASURE CPU runner|
|14|Generation speed|MEASURE|MEASURE|Official claim 3x realtime on 8 CPU cores; independently MEASURE|Realtime/streaming claimed; independently MEASURE|MEASURE|
|15|Free-use limits|current baseline|VERIFY CURRENT|local model; no API quota dependency|local model; no API quota dependency|local model; no API quota dependency|
|16|YouTube/TikTok license|VERIFY TERMS|VERIFY TERMS|Official HF model card declares MIT; user/reference voice rights remain caller responsibility|Official HF model card declares Apache-2.0; bundled reference prompt provenance not separately certified|Apache-2.0 weights/model repository; bundled voicepacks are distributed in same repository, but no separate per-voice rights statement located yet|
|17|Commercial output|VERIFY|VERIFY|PROVISIONAL: exact model card/checkpoint MIT; user/reference voice and dependency rights still gated|PROVISIONAL: exact model card/checkpoint Apache-2.0; bundled reference prompt and dependency chain still gated|PROVISIONAL: model/weights explicitly production-deployable under Apache-2.0; voicepack provenance and GPLv3 espeak-ng distribution obligations still audit|
|18|Model quality/size|service|service|110M params official|~0.1B TTS + ~20M tokenizer|~82M params; repository snapshot ~hundreds MB|
|19|Integration complexity|MEASURE|MEASURE|Python/local; reference clip supported/used in documented generation; MEASURE dependencies/cold start|Python/local + tokenizer + voice prompt; MEASURE dependencies/cold start|Python/local; bundled voicepacks; espeak-ng phonemization dependency; MEASURE cold start|
|20|Availability risk|service dependency|preview/free-tier dependency|local model; upstream/download dependency|local/upstream dependency|local/upstream dependency|

## Evidence captured 2026-09-15

- Gemini 2.5 Flash Preview TTS pricing documentation exposes a free tier, but explicitly labels the TTS model preview and notes preview models can change and have stricter rate limits. This is not sufficient to certify commercial-output terms or long-term availability.
- The official Hugging Face model card `OpenMOSS-Team/MOSS-TTS-Nano-100M` currently declares `apache-2.0`, describes the model as ~0.1B parameters, supports 20 languages including English, states that it can run directly on CPU, and states streaming can run on a 4-core CPU. It documents direct Python inference and a packaged CLI. This is stronger evidence than repository-code licensing alone because it is attached to the distributed model card/checkpoint.
- The MOSS official workflow is voice cloning: its documented local inference and CLI examples use a prompt/reference audio file, and the model repository contains an example prompt under `assets/audio`. Apache-2.0 on the model/checkpoint does not by itself prove the provenance or commercial voice/personality rights of that example recording. Factory commercial certification therefore requires either explicit rights evidence for the selected prompt or a Factory-owned/licensed reference recording. The bundled example prompt must not be assumed commercially cleared merely because it ships in an Apache-licensed repository.
- The exact `OpenMOSS/MOSS-TTS-Nano` root LICENSE was separately inspected and is Apache License 2.0. Repository-code license and official HF model-card license are independently captured rather than inferred from one another.
- Kokoro-82M model-card evidence identifies ~82M parameters and Apache-2.0 model weights and explicitly describes production deployment. The same official model repository contains the distributed voicepack files and `VOICES.md`, including named voicepacks such as Bella/Sarah and a mixed `af` voice. However, the material inspected so far does not provide a separate per-voice provenance/commercial-rights grant beyond the repository/model licensing metadata. Treat voicepack rights as an explicit remaining audit item rather than silently inheriting the model license.
- Kokoro's official model card also explicitly identifies `espeak-ng` as a GPLv3 dependency while the model weights are Apache-2.0 and inference code is MIT. GPLv3 is not a commercial-use prohibition, but it is a distribution/compliance consideration for the packaged Factory dependency chain and must be handled deliberately rather than labelled permissive-only.
- The official Hugging Face model card `ResembleAI/chatterbox-nano` itself declares `mit`. It identifies Nano as a 110M English model, CPU/on-device oriented, with an official claim of about 3x realtime on 8 CPU cores and native paralinguistic tags. The Chatterbox family supports generation with an audio prompt/reference voice. The model/checkpoint license does not confer rights to arbitrary user-supplied reference audio; Factory must use only a reference recording whose voice/personality and recording rights are controlled or licensed for the intended commercial output.
- Chatterbox-Nano outputs include provenance watermarking according to the vendor's Nano release material. Preserve this behavior; do not use third-party forks whose purpose is watermark removal.

## Licensing gate

For every local candidate, certification requires four separately recorded facts where applicable: (1) repository/code license, (2) model-weight/checkpoint license, (3) voice/model-card or other asset restrictions, and (4) restrictions affecting commercial generated output. A permissive repository license alone is never sufficient evidence for all four.

An official model-card license closes the checkpoint-license evidence only when the card is the authoritative card for the exact model being benchmarked. It does not silently license user-supplied reference voices, separately hosted tokenizers/phonemizers, bundled voice prompts, third-party wrappers/conversions, or training/reference datasets.

For voice-cloning engines, Factory certification additionally requires positive provenance for the selected reference recording. Absence of an explicit restriction is not positive evidence of personality/recording rights. Prefer a Factory-owned or explicitly commercially licensed reference voice over bundled demo prompts when provenance is unclear.

Copyleft runtime dependencies are not automatically disqualifying for commercial use. They must instead be recorded with their actual distribution/compliance obligations and architecture impact before the final production dependency set is certified.

## Measurement contract

All engines must synthesize the exact same benchmark corpus. Record cold-start time, synthesis time, output duration, realtime factor (generation_seconds/audio_seconds), peak RAM where measurable, artifact size, failure/retry count, and whether GPU was used. Listening samples must be randomized to opaque IDs before human scoring.

Vendor performance claims are evidence for feasibility only, never substitutes for Factory measurements. CPU speed, RAM, cold-start and RTF must be measured on the actual GitHub Actions benchmark environment before a candidate can pass M6.0.

No engine may become production-selected during M6.0. M6.0 ends at HUMAN_REVIEW_REQUIRED after the technical matrix and blind sample package are complete.


## Qualification update — 2026-09-19

The frozen 12-case corpus now has complete cryptographically bound full-corpus runtime packages for Edge legacy, Kokoro `af_heart`, and Chatterbox-Nano built-in voice. Subjective quality dimensions (naturalness, intonation, emotionality, pronunciation quality, prosodic appropriateness) remain UNKNOWN until blind human listening; runtime success must not be converted into a quality score.

| Dimension | Edge legacy | Kokoro `af_heart` | Chatterbox-Nano |
| --- | --- | --- | --- |
| Frozen corpus completeness | PASS 12/12 | PASS 12/12 | PASS 12/12 |
| Python automation | PASS | PASS | PASS |
| GitHub Actions CPU fit | PASS | PASS | PASS |
| GPU required in measured run | PASS: no GPU | PASS: no GPU | PASS: no GPU |
| Generation speed | PASS technical; warm RTF 0.065–0.224 across corpus | PASS technical; warm RTF 0.536–0.563 | PASS technical; warm RTF 0.873–1.227 |
| Source/audio cryptographic binding | PASS | PASS | PASS |
| Naturalness | UNKNOWN — human blind review required | UNKNOWN — human blind review required | UNKNOWN — human blind review required |
| English quality | UNKNOWN — human blind review required | UNKNOWN — human blind review required | UNKNOWN — human blind review required |
| Intonation | UNKNOWN — human blind review required | UNKNOWN — human blind review required | UNKNOWN — human blind review required |
| Emotionality | UNKNOWN — human blind review required | UNKNOWN — human blind review required | UNKNOWN — human blind review required |
| Pronunciation stability | UNKNOWN — human blind review required | UNKNOWN — human blind review required | UNKNOWN — human blind review required |
| Commercial voice/reference rights | Existing production baseline; terms remain separately governed | FAIL for M6 production qualification pending explicit `af_heart` rights | FAIL for M6 production qualification pending explicit built-in `conds.pt` voice rights |
| Production qualification | Baseline only; no M6 selection made | FAIL-CLOSED pending voicepack rights | FAIL-CLOSED pending built-in voice rights |

MOSS-TTS-Nano remains technical-only and fail-closed for production qualification pending explicit rights for the tested reference audio. Gemini runtime remains blocked by free-tier credential/billing attestation; no paid request is permitted. Neither is silently scored as though equivalent full-corpus listening evidence existed.

A blind package must keep the reviewer-facing artifact free of engine names and place the engine mapping in a separate audit artifact. Every reviewer sample must bind `sample_id`, case, exact frozen source SHA-256 and audio SHA-256. The audit mapping additionally binds engine version/commit and synthesis configuration. Human scores are not yet present, so M6.0 must not advance to M6.1.


## Human review gate result — 2026-09-20

The human gate did not approve M6.0. Listening feedback: intonation improved, but the male voice remains noticeably robotic and emotionally detached. Therefore naturalness/human-likeness is FAIL for the reviewed production-quality target and M6.1 remains blocked.

Targeted 2026 research adds Qwen3-TTS, IndexTTS-2.5 and CosyVoice3 to the research screen. F5-TTS is fail-closed for the Factory's zero-cost commercial constraint because official pretrained weights are CC-BY-NC. Fish Speech/Fish Audio S2 is fail-closed because its March 2026 research license requires a separate commercial license. No model is promoted to production by research claims alone.
