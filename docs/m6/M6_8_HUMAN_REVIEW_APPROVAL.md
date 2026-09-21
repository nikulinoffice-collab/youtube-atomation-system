# M6.8 Human Review Approval

Status: HUMAN_REVIEW_APPROVED_M6_8
Recorded: 2026-09-21

## Qualified candidate

- Runtime candidate SHA: `b2e6a9a7bddbc34ff0ea025566d64d95c14157ef`
- GitHub Actions run: `35622794103`
- Job: `106409715089`
- Human-review artifact: `10650630260`
- Artifact digest: `sha256:0b984dd2d1d6bb351018af60bd13d60bd11bf558d7e6ba2f153fcfa8680cf519`
- Review audio: `complete_short_unmastered.wav`
- Voice: Qwen3-TTS 12Hz 0.6B CustomVoice / English / Ryan
- Runtime result: PASS
- Complete Short duration: 32.08 s
- Sample rate: 24000 Hz

## Human review

The repository owner reviewed the qualified M6.8 audio and explicitly accepted the voice-over quality on 2026-09-21.

This closes the M6.8 human-quality gate for the exact qualified artifact above. It is not a general naturalness certification for arbitrary future synthesis.

## Published-license review

The previous project-local requirement for a separate Ryan-specific permission was re-evaluated against the published upstream materials.

Evidence reviewed:
- The official Qwen `Qwen3-TTS-12Hz-0.6B-CustomVoice` checkpoint is published as Apache-2.0.
- The checkpoint is explicitly the CustomVoice variant and ships nine supported premium timbres.
- Ryan is a supported predefined speaker of CustomVoice, not a user-supplied reference-audio clone.
- Qwen's official Apache-2.0 example invokes `generate_custom_voice(... speaker="Ryan" ...)`.
- The official `qwen-tts` package is Apache-2.0.
- No separate Ryan-specific non-commercial, research-only, no-monetization, or additional preset-voice license was identified in the published upstream materials reviewed on 2026-09-21.

Project decision: the previously invented requirement for separate affirmative Ryan-specific permission is removed. Local use of the built-in Ryan speaker is governed by the published upstream terms that apply to the CustomVoice checkpoint/package, subject to normal Apache-2.0 compliance and any later-discovered applicable restriction.

This is an engineering licensing decision based on the published materials, not a warranty that no third-party right can ever exist. If upstream terms materially change or a specific applicable restriction is discovered, publishing must fail closed pending re-review.

## Quality preservation

This rights-state change does not alter synthesis code, model weights/revision, Ryan speaker selection, VoicePlan, rendering, mastering, alignment, QC thresholds, or the human-approved audio configuration. The M6.8 qualified voice quality is therefore unchanged by this commit.

## Required state

- `human_review_required=false` for this exact M6.8 artifact.
- `human_review_approved=true`.
- `naturalness_claimed=false`.
- `ryan_published_terms_review=PASS`.
- `separate_ryan_permission_required=false`.
- `publishing_rights_blocker=false` under the reviewed published terms.
- `production_migration_permitted=true` subject to M6.9 technical qualification and rollback gates.
- `m6_9_autostart_permitted=false`.

Next permitted action: begin M6.9 only as an explicit, controlled production-migration milestone. Preserve the exact human-approved Ryan synthesis configuration until a separately qualified change is approved.
