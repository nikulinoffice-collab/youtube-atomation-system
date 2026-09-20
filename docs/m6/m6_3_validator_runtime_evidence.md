# M6.3 fail-closed VoicePlan validator — completion evidence

Date: 2026-09-21
Status: PASS

## Completion qualification

- Branch: `factory-v1-voice-m6`
- Qualification workflow: `.github/workflows/m6-qualification.yml`
- Tested commit: `29e45ee915458b2469e6567451b08331614f32a7`
- GitHub Actions run: `35540439861`
- Job: `106156983317`
- Result: SUCCESS
- Runner: Ubuntu 24.04.5 (`ubuntu-24.04` image `20260907.300.1`)
- Python: CPython 3.11.16
- pytest: 9.1.1
- Test command: `python -m pytest -q tests/test_m6_voice_script.py tests/test_m6_voice_plan.py tests/test_m6_voice_plan_validator.py`
- Exact result: `28 passed in 0.06s`

## Gate evidence

The qualified revision includes the fail-closed M6.3 VoicePlan validator and its positive/boundary/adversarial suite, together with M6.1 and M6.2 regressions. The validator checks provenance/version compatibility, complete ordered spoken coverage, duplicate/reordered/missing blocks, semantic roles, bounded WPM/rate/pause/energy/pitch controls, emphasis spans, intonation contours and pronunciation references. Invalid plans produce explicit machine-readable validation errors and are rejected before TTS.

M6.3 completion gate is satisfied for the exact revision above. Later semantic changes to M6.1-M6.3 require appropriate requalification.

## Invariants

Production Edge voice was not changed. Frozen M5 was not changed. Ryan remains development/internal-test only and publishing remains fail-closed. No paid service, billing, secret mutation or publishing action was used.
