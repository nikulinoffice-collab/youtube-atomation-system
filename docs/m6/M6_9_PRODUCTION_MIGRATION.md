# M6.9 Production Migration

Status: IN_PROGRESS

M6.9 migrates the voice factory to the exact Ryan configuration approved in M6.8. It must not alter voice quality parameters.

## Immutable qualified voice identity

- Model: Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
- Model revision: 85e237c12c027371202489a0ec509ded67b5e4b5
- Qwen source commit: 022e286b98fbec7e1e916cb940cdf532cd9f488e
- Speaker: Ryan
- Language: English
- Human-review candidate: b2e6a9a7bddbc34ff0ea025566d64d95c14157ef
- Run: 35622794103
- Job: 106409715089
- Artifact: 10650630260

## Migration gates

Production routing may be enabled only after all of the following pass:

1. M6.8 human approval remains valid.
2. Published-terms review remains clear.
3. Frozen model, revision, speaker, language, instruction and generation parameters are byte-for-byte unchanged from the qualified configuration.
4. The existing production voice remains an explicit rollback target.
5. Failure of production qualification leaves the existing production route active.
6. M6.1-M6.8 regression qualification passes on the migration revision.
7. A production-path canary produces lossless audio and passes the existing M6.8 QC/alignment checks before routing is switched.

No DSP, sampling, VoicePlan, mastering or Ryan parameter may be changed merely to complete migration.

## Rollback

Migration is transactional: prepare -> qualify -> canary -> switch. Any failure before switch aborts migration. Any post-switch health failure must restore the previous production voice route without changing the approved Ryan configuration.

## Current state

The migration contract is now defined, but production routing is not switched by this document. The next implementation unit is the machine-enforced migration/rollback gate plus M6.9 qualification tests.
