# M6.4 Qwen3/Ryan adapter — unit qualification evidence

Date: 2026-09-21
Status: UNIT CONTRACT PASS — real Qwen3/Ryan synthesis runtime qualification remains required before M6.4 completion.

## Bound clean qualification

- Branch: `factory-v1-voice-m6`
- Tested commit: `b9fabfb73ff0641f0b4fbe5c9de86119cf9241cc`
- GitHub Actions run: `35556169565`
- Job: `106200130167`
- Workflow: `.github/workflows/m6-qualification.yml`
- Event: push
- Runner: Ubuntu 24.04.5 (`ubuntu-24.04`, image `20260907.300.1`)
- Python: CPython 3.11.16
- pytest: 9.1.1
- Exact command: `python -m pytest -q tests/test_m6_voice_script.py tests/test_m6_voice_plan.py tests/test_m6_voice_plan_validator.py tests/test_m6_tts_adapter.py tests/test_m6_qwen3_adapter.py`
- Exact result: `38 passed in 0.07s`
- Conclusion: SUCCESS

The run explicitly verified `GITHUB_SHA` equals the checked-out HEAD before tests. It qualifies the generic TTS adapter contract, pinned Qwen3/Ryan adapter unit/mock behavior, and M6.1–M6.3 regressions on the exact revision above.

## Frozen runtime identity carried by the qualified adapter

- Engine source: `QwenLM/Qwen3-TTS`
- Source commit: `022e286b98fbec7e1e916cb940cdf532cd9f488e`
- Package version: `0.1.1`
- Model: `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`
- Model revision: `85e237c12c027371202489a0ec509ded67b5e4b5`
- Language: English
- Development speaker: Ryan
- Frozen runtime request: CPU / float32
- Production enabled: false
- Paid services: false

These pins are configuration identity only. They are not evidence that the real model successfully runs on GitHub-hosted CPU. That claim remains fail-closed until a special runtime qualification succeeds.

## Remaining M6.4 gate

Run one special, non-paid real Qwen3/Ryan synthesis qualification on an exact revision. Persist lossless WAV plus machine-readable provenance/metrics covering source/model revisions, speaker, device, sample rate, channels, synthesis duration, audio duration, RTF and peak RAM. Do not claim CPU compatibility before that run succeeds. If the runtime cannot execute within the free GitHub-hosted environment, record the exact observed blocker instead of weakening the gate.

Production Edge remains unchanged. Ryan remains development/internal-test only and publishing remains fail-closed.