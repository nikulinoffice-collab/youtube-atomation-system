# M6.0 Gemini TTS Runtime Gate

Status: `BLOCKED_BY_FREE_TIER_CREDENTIAL_ATTESTATION`

Evidence date: 2026-09-16.

## Repository/configuration truth

The M6 branch contains only the production `publish.yml` workflow under `.github/workflows/`. That workflow is manual (`workflow_dispatch`), uses least-privilege `contents: read`, and references an existing repository secret named `GEMINI_API_KEY` for the existing Factory generation path. It explicitly fails if that secret is absent. No temporary Gemini TTS benchmark workflow is present.

The existence/reference of `GEMINI_API_KEY` proves only that the repository was designed to receive a Gemini credential. It does **not** prove that the credential belongs to a Gemini Developer API Free Tier project, that billing is unattached, or that a request cannot be charged under a paid tier. GitHub does not expose secret values here, and M6 intentionally does not read, print, rotate, replace, or otherwise inspect secret material.

## Gate decision

The documentation-level zero-cost gate remains `ZERO_COST_PATH_EXISTS` for `gemini-2.5-flash-preview-tts`, as recorded in `dependency_audit.md`. The runtime gate is stricter: a real API benchmark is permitted only when the credential/project can be positively identified as Free Tier without enabling billing and without a paid fallback.

Current repository configuration cannot establish that billing/tier property. Therefore M6 must **not** issue a Gemini TTS API request using the existing secret merely because the secret exists. Runtime status is `BLOCKED_BY_FREE_TIER_CREDENTIAL_ATTESTATION`, not technical FAIL and not engine disqualification.

No API request was made while evaluating this gate. No secret value was accessed or exposed. No billing configuration, paid service, publishing path, production voice behavior, M5 baseline, or `main` branch was changed.

## Consequence for M6.0

Gemini remains in the required comparison with documentation-level capability/free-tier evidence and explicit runtime `UNKNOWN/BLOCKED` fields. M6.0 may continue with reproducible frozen-corpus benchmark/manifest and blind-listening evidence for engines that have already passed safe shadow runtime qualification. The human review package must make the missing Gemini runtime sample explicit rather than fabricating or substituting one.
