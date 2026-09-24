# M6.9 Production Migration

Status: IN_PROGRESS

M6.9 migrates the voice factory to the exact Ryan configuration approved in M6.8. It must not alter voice quality parameters.

## Immutable qualified voice identity

- Model: Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
- Model revision: 85e237c12c027371202489a0ec509ded67b5e4b5
- Qwen source commit: 022e286b98fbec7e1e916cb940cdf532cd9f488e
- qwen-tts: 0.1.1
- Speaker: Ryan
- Language: English
- Human-review candidate: b2e6a9a7bddbc34ff0ea025566d64d95c14157ef
- Human-review run: 35622794103
- Human-review job: 106409715089
- Human-review artifact: 10650630260

## Migration gates

Production routing may be enabled only after all of the following pass:

1. M6.8 human approval remains valid.
2. Published-terms review remains clear.
3. Frozen model, revision, speaker, language, instruction and generation parameters are byte-for-byte unchanged from the qualified configuration.
4. The existing production voice remains an explicit rollback target.
5. Failure of production qualification leaves the existing production route active.
6. M6.1-M6.8 regression qualification passes on the migration revision.
7. A production-path canary produces lossless audio and passes the existing M6.8 QC/alignment checks before routing is switched.
8. The downstream renderer and QC accept the Ryan lossless WAV without stale MP3 assumptions.
9. The exact production-switch revision passes persistent qualification and a post-switch non-publishing health canary.
10. Automatic rollback to Edge/GuyNeural is verified.

No DSP, sampling, VoicePlan, mastering or Ryan parameter may be changed merely to complete migration.

## Full non-publishing production-path canary — PASS

Qualified/canary revision: `e856a5b36af8250ecfafa1e14ffc66fe88f5ae42`.

Persistent M6 Qualification:
- Run: 35980861958
- Result: SUCCESS
- Exact revision: e856a5b36af8250ecfafa1e14ffc66fe88f5ae42

Full M6.9 production-path canary:
- Run: 35980862051
- Job: 107572145056
- Result: SUCCESS
- Artifact: 10799804071
- Artifact digest: `sha256:f5ef39e261d0aecbd8cbe9d43e3796c036002cc4dc3e0fe92a684f1ed0b55111`
- Environment: GitHub-hosted Ubuntu 24.04.5 LTS / ubuntu-24.04 image 20260920.314.1 / CPython 3.11.16 / CPU path
- Model: Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
- Model revision: 85e237c12c027371202489a0ec509ded67b5e4b5
- Qwen source commit: 022e286b98fbec7e1e916cb940cdf532cd9f488e
- qwen-tts: 0.1.1
- WhisperX: 3.8.6
- Speaker/language: Ryan / English
- Audio: lossless mono WAV, 24000 Hz, 23.28 s
- Canonical alignment: expected 53, aligned 53, observed 53; exact normalized stream PASS
- Captions: 51 authoritative words grouped into 10 cues; within authoritative narration PASS
- Renderer: PASS; 1080x1920, 30 fps, 8 contiguous scenes, audio/video streams present, source-card contract PASS
- Visual QC: PASS; unique selected assets, maximum same-category run 1, valid motion parameters, candidate→asset→renderer chain PASS
- Final QC: PASS; required artifacts present, voice/timeline match, final duration/voice match, captions within narration, timing/provenance preserved
- Publishing/upload: NOT PERFORMED
- Frozen Ryan quality configuration: unchanged

The full canary proves the real non-publishing chain: Qwen3/Ryan -> lossless WAV -> WhisperX forced alignment -> canonical production narration timeline -> captions -> deterministic non-paid visual fixtures -> production renderer -> final MP4 -> visual QC -> production QC.

## Rollback

Migration is transactional: prepare -> qualify -> canary -> switch. Any failure before switch aborts migration. Any post-switch health failure must restore the previous production voice route without changing the approved Ryan configuration.

Rollback target: Edge `en-US-GuyNeural` only. Ryan must not depend on Edge-only runtime dependencies.

## Current state

Prepare, exact-revision qualification, real Ryan/canonical alignment/captions canary, downstream lossless-WAV renderer integration, and full non-publishing renderer/QC canary are PASS.

The production workflow is staged for `m6-ryan`, but final migration is not COMPLETE yet. Before completion, the production workflow's own verification/package logic must be audited for remaining MP3-only assumptions, the switch/automatic-rollback contract must be machine-verifiable, the exact final production revision must pass persistent qualification, and a post-switch non-publishing health canary must PASS. Temporary canary infrastructure must remain until final evidence is persisted.
