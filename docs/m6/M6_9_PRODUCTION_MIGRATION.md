# M6.9 Production Migration

Status: COMPLETE

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

## Final M6.9 closure evidence

Executable production revision: `27e6457fca39be60df82b9c85f389a68b58e03db`.

Persistent M6 Qualification:
- Run: 36368166353
- Job: 108758632217
- Result: SUCCESS
- Exact revision: 27e6457fca39be60df82b9c85f389a68b58e03db
- Regression result: 117 passed, 1 skipped

Route-bound post-switch non-publishing health canary:
- Run: 36368166624
- Job: 108758632885
- Result: SUCCESS
- Exact revision: 27e6457fca39be60df82b9c85f389a68b58e03db
- Regression result: 105 passed
- Evidence artifact: 10947933381
- Artifact digest: `sha256:c7ece850b269b38443d6b7ace60ff390a68dde0fed5d7d7d601f36a1da035ac7`
- Production route source: committed `config/m6/production_voice_route.json`
- Active backend: `m6-ryan`
- Rollback backend/voice: `edge` / `en-US-GuyNeural`
- Publishing enabled: false
- Publishing/upload invocation: NOT PERFORMED; the canary regression and workflow explicitly require that `upload_agent.py` is absent from the canary workflow.
- Audio: lossless mono WAV, 24000 Hz, 23.68 s
- Canonical alignment: expected/aligned/observed 53/53/53; exact normalized stream PASS
- Renderer: PASS; 8 rendered segments; candidate-to-asset-to-renderer chain valid
- Visual QC: PASS
- Final QC: PASS

Rollback verification is covered by the M6.9 qualification/adversarial contract: failure before switch leaves the prior route unchanged, successful switch leaves Ryan active, and failed/exception post-switch health restores the exact Edge/GuyNeural rollback state while publishing remains disabled.

Frozen-state verification:
- `config/m6/qwen3_ryan_frozen.json` remains the approved immutable Ryan/Qwen identity and generation configuration.
- Frozen branch `factory-v1-storyboard` remains at `ddd55af7ed3f7bd418b078140909750d758519bb`.
- No paid service, billing, new secret, publishing action, social/video upload, or quality-gate weakening was used for closure.

This evidence commit is documentation-only. The exact executable production revision qualified and exercised by the route-bound real-runtime canary remains `27e6457fca39be60df82b9c85f389a68b58e03db`.

## Current state

M6.9 is COMPLETE. The committed production route resolves to Ryan, persistent qualification and the route-bound full-path post-switch health canary passed on the exact executable production revision, renderer/visual/final QC passed, automatic Edge/GuyNeural rollback is regression-verified, publishing remains disabled and the canary did not invoke the upload/publishing path, final evidence is persisted, and both the frozen Ryan configuration and frozen storyboard branch remain unchanged.
