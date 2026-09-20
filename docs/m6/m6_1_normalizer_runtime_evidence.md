# M6.1 deterministic Voice Script — completion evidence

Date: 2026-09-20
Status: PASS

## Completion qualification

- Branch: `factory-v1-voice-m6`
- Qualification workflow: `.github/workflows/m6-qualification.yml`
- Tested commit: `d57790be2ec099cfeeea7089176172427263440c`
- GitHub Actions run: `35532131251`
- Event: push
- Result: SUCCESS
- Runner contract: Ubuntu 24.04, CPython 3.11
- Test command: `python -m pytest -q tests/test_m6_voice_script.py`

The qualified revision contains the M6.1 normalizer fix at `da1a7e89821faa7c0d1e7e0406318aec5f454285` plus the persistent qualification workflow. The successful run therefore exercises the corrected longest-match lexicon behavior and stable lexicon provenance together with the complete M6.1 suite.

## Gate evidence

The bound suite covers immutable canonical `display_text`, deterministic `spoken_text`, exact display↔spoken replacement spans, normalization provenance, lexicon version/hash provenance, integers/decimals, years, ISO dates, times, currencies, percentages, units, acronyms, proper nouns/identity entries, technical terms, longest-match precedence, adversarial non-matches, deterministic repeated output, and frozen benchmark-corpus validation.

M6.1 completion gate is satisfied for the version represented by this evidence. Any later semantic change to M6.1 requires requalification.

## Invariants

Production Edge voice was not changed. Frozen M5 was not changed. Ryan remains development/internal-test only; publishing remains fail-closed. No paid service, billing, secret mutation or publishing action was used.
