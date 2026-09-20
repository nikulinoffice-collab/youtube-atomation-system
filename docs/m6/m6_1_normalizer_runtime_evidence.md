# M6.1 normalizer runtime evidence

Date: 2026-09-20
Status: EXPANDED SUITE PASS — clean CI validates the current dates/time/units expansion; M6.1 completion gate remains open only for final required abbreviation/name/technical-term/adversarial coverage and explicit final gate evidence.

## Baseline qualification

- Tested commit: `b9972890740d36876fad2619d88c9a8def25fda7`
- GitHub Actions run: `35509318103`
- Job: `106074355034`
- Result: SUCCESS — `5 passed in 0.02s`

## Expanded qualification

- Branch: `factory-v1-voice-m6`
- Tested commit: `9d251f4849f66e51adef57bbe2e09cffd1dc518e`
- GitHub Actions run: `35515076950`
- Job: `106089532631`
- Runner: Ubuntu 24.04.5 (`ubuntu-24.04` image `20260907.300.1`)
- Python: CPython 3.11.16
- pytest: 9.1.1
- Test command: `python -m pytest -q tests/test_m6_voice_script.py`
- Exact result: `9 passed in 0.03s`
- Conclusion: SUCCESS

## What the expanded run proves

The current M6.1 implementation, including deterministic ISO-date, time and physical/technical-unit normalization added before this run, executes successfully in a clean GitHub-hosted runner. The suite also exercises deterministic output, immutable canonical display text, display↔spoken mapping integrity, rule precedence, frozen-corpus coverage and adversarial invalid date/time behavior represented by the bound test revision.

The result is bound to the exact tested commit above; later changes require new evidence before being included in the completion claim.

## Remaining M6.1 gate work

Before declaring the complete milestone PASS, finish explicit required abbreviation/acronym, proper-name and technical-term adversarial/golden coverage and verify the final complete suite in clean CI. Persist final completion evidence only after that bound run succeeds.

Production Edge was not changed. Frozen M5 was not changed. Ryan remains development/internal-test only and publishing remains fail-closed. No paid service, billing, secret change or publishing was used.
