# M6.1 normalizer runtime evidence

Date: 2026-09-20
Status: PARTIAL PASS — baseline normalizer CI validated; M6.1 completion gate remains open for remaining normalization coverage.

## Bound revision and run

- Branch: `factory-v1-voice-m6`
- Tested commit: `b9972890740d36876fad2619d88c9a8def25fda7`
- GitHub Actions run: `35509318103`
- Job: `106074355034`
- Runner: Ubuntu 24.04.5 (`ubuntu-24.04` image `20260907.300.1`)
- Python: CPython 3.11.16
- pytest: 9.1.1
- Result: SUCCESS
- Test command: `python -m pytest -q tests/test_m6_voice_script.py`
- Exact result: `5 passed in 0.02s`

## What this proves

The current M6.1 baseline implementation and its existing tests execute successfully in a clean GitHub-hosted runner after explicitly installing the test dependency. The earlier failure was infrastructure-only (`pytest` absent), not a normalizer failure.

This run validates the existing deterministic-output, mapping-integrity, immutable-display-text/rule-precedence and current frozen-corpus checks represented by `tests/test_m6_voice_script.py` at the bound revision. It does not by itself close the full M6.1 completion gate.

## Remaining M6.1 gate work

Before M6.1 can be declared complete, expand deterministic normalization/adversarial coverage for dates, times, units and remaining required abbreviation/name/technical-term cases; then rerun the complete M6.1 suite and persist final evidence.

Production Edge was not changed. Frozen M5 was not changed. Ryan remains development/internal-test only and publishing remains fail-closed. No paid service, billing, secret change or publishing was used.
