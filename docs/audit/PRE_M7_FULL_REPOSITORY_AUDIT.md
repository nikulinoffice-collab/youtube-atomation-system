# PRE-M7 Full Repository Audit

Status: PASS — PRE-M7 FULL REPOSITORY AUDIT COMPLETE (2026-10-23)

## Baseline
- Active branch: `factory-v1-voice-m6`
- Starting audited HEAD: `a5ba707fe7ca96d3ce4ef6ba5ab1b3ba18d72e70`
- Frozen branch: `factory-v1-storyboard`
- Frozen SHA verified: `ddd55af7ed3f7bd418b078140909750d758519bb`
- M6.9 production behavior and frozen Ryan/Qwen identity are immutable audit constraints.

## Gate status
1. Inventory — PASS
2. Architecture — PASS
3. Line-by-line static audit — PASS
4. Dependencies/external interfaces — PASS
5. Data flow/contracts — PASS
6. GitHub Actions/automation — PASS
7. Tests/QC/fail-closed — PASS
8. Security/cost/publishing — PASS
9. Controlled cleanup/refactor — PASS
10. Clean-room E2E qualification — PASS

## Findings ledger
| ID | Severity | Finding | Status |
|---|---|---|---|
| AUD-P1-001 | P1 | Draft/full-production dependency environment previously lacked exact shared enforcement for the validated Ryan runtime and the complete production graph. DIRECT_BLOCKS=[4,6,7,10]. | CLOSED — shared 189-package exact constraints lock is enforced by qualification and draft workflows; `qwen-tts==0.1.1` and `whisperx==3.8.6` remain frozen; dependency-contract regression executed in exact-SHA M6 Qualification `38703875490`, job `116318345733`, on `0fdea313c8446d2112859d4fd5420e6e3b31ffcd`: SUCCESS, 128 passed / 1 skipped, `pip check` PASS. |
| AUD-P1-002 | P1 | Script topic history previously used `agents/output/recent_topics.json`; production code now uses canonical `agents/state/recent_topics.json` with state-directory creation and contract tests. DIRECT_BLOCKS=[5,7,10]. | CLOSED — implementation `22626f8b` and tests `36357bd5` are contained in exact-SHA-qualified `a65f7c69598f68868dce12f1efafb4079d2b53cb`; M6 Qualification run `37205491751`, job `111445703429` SUCCESS and executed the state-contract test suite. |
| AUD-P1-003 | P1 | Cross-run anti-repeat history was not persisted across read-only draft runs. DIRECT_BLOCKS=[5,6,7,10]. | CLOSED — cache restore/save and explicit fail-closed cache-miss bootstrap in `.github/workflows/publish.yml@09ee25fae9f895484d295abd084d4b6c0c29628d`; malformed restored-state rejection in `agents/script_agent.py@ff9bdaf2632776ac580fb1b7e04e06098bc778ee`; restored/empty/corrupt/continuity regressions in `tests/test_pre_m7_state_contracts.py@6e52e96b5e4a9375e5d57fc0339669256d5b4d33`. Exact executable SHA `7e898c57108966d0e4c81e07a218d1a681104a88`, M6 Qualification run `39925089835`, job `120319389641` SUCCESS (140 passed / 1 skipped); no contents:write or publishing. Cache eviction/miss fails closed unless explicitly bootstrapped. |
| AUD-P1-004 | P1 | `upload_agent.py` independently executable publishing entry point remediated with default-private plus explicit `YOUTUBE_PUBLISH_AUTHORIZED=true` as the first `main()` operation before artifact discovery/OAuth/API/network. DIRECT_BLOCKS=[8,10]. | CLOSED — corrected implementation `94b0f477b54b9f0655c8b627f66335eb7fa9b6f4` contained in exact-SHA-qualified `a65f7c69598f68868dce12f1efafb4079d2b53cb`; M6 Qualification run `37205491751`, job `111445703429` SUCCESS. |
| AUD-P1-005 | P1 | Validated M5.4 Source Card and controlled still-motion contract was absent from `agents/video_agent.py@01e6f697b3810bca8e3ce3541ca112243dc927d1` relative to frozen `agents/video_agent.py@6b9e20817e59240032c65aaadbb95bb00fe4ba8b`. DIRECT_BLOCKS=[5,7,10] — visual fidelity and rendering/QC, not workflow qualification. | CLOSED — M5.4 Source Card, caption-safe layout and five still-motion paths restored in `agents/video_agent.py@389e440c280984824956229cd2b62db6e5677fd2`, with explicit fail-closed source-URL validation and no stock downgrade; M6.9 `resolve_voice_artifact` preserved. Focused positive/negative/adversarial tests `tests/test_pre_m7_visual_contracts.py@41386c5b3c430cc99b1510b799ad9f89779958d8` executed in exact-SHA M6 Qualification `39932656805`, job `120344462909`, on `0ad2953c45e81ca31e08d86107804390d7400245`: SUCCESS, 160 passed / 1 skipped, locked install and pip check PASS. Synthetic fixture/contract tests do not constitute clean-room E2E. |
| AUD-P1-006 | P1 | Run-bound producer/schema/payload/upstream SHA-256 integrity across script, narration timeline, storyboard, ranked candidate and asset manifests, selected media, renderer, final MP4 and QC/package. DIRECT_BLOCKS=[5,7,10]; Gate10 additionally requires clean-room E2E independent of this finding. | CLOSED — all producer/consumer integrity checks and adversarial regressions qualified at executable SHA `747adc016cab245959d4e3e45d427d1ea67e09a2`, M6 Qualification run `39961880015`, job `120441632589` SUCCESS (221 passed, 1 skipped; locked install, `pip check` PASS). Renderer/QC and package checks reject stale, wrong-producer/schema/run, tampered source/media, and restored-cache substitutions; final clean-room production E2E remains Gate10, not a P1 closure substitute. |
| AUD-P1-007 | P1 | Qualification previously had watched-path and test-discovery blind spots. DIRECT_BLOCKS=[6,7,10] because changes could evade executable qualification and regression. | CLOSED — `.github/workflows/m6-qualification.yml@f6bc535beabd9718add211c705c02306dd3971f6` watches all three workflows, runtime directories, production lock and benchmark corpus; push/M6.9 runs all `tests/`. Focused regression `tests/test_pre_m7_dependency_contracts.py@b60b3e5852b59e4d524d28a96c3d47b67acdcf00` executed in exact-SHA M6 Qualification `39925566753`, job `120320966484`, SUCCESS (144 passed / 1 skipped). |
| AUD-P1-008 | P1 | Edge rollback executable defect was corrected and a direct no-network rollback synthesis regression was added. DIRECT_BLOCKS=[6,7,10]. | CLOSED — exact-SHA qualification succeeded for `140a5d4c454fa06b0bfa553d779e85f641893344` in M6 Qualification run `37103103913`; fix remains contained in latest qualified executable `0fdea313c8446d2112859d4fd5420e6e3b31ffcd`. |
| AUD-P1-009 | P1 | Gate10 one-shot workflow validated the committed Ryan route but did not export it to downstream voice generation, so the real clean-room run silently selected Edge rollback. DIRECT_BLOCKS=[10] only; the normal draft workflow already exported the Ryan route. | CLOSED — `.github/workflows/m6-qualification.yml@eda36200b5a4ed113abd1f7b5d6c7446450b271b` exports validated `FACTORY_VOICE_BACKEND=m6-ryan` via `GITHUB_ENV`; focused regression `tests/test_pre_m7_dependency_contracts.py@42852567756895ef861861ea7d7adac4a5bf77ac` executed in exact-SHA qualification `40004314075` / job `120588205873` (SUCCESS, 224 passed / 1 skipped) on `65bad44978d7b2a4f3509eb21ef48c760bf3ab9b`. Real Ryan clean-room job `120589521499` SUCCESS on the same SHA; no publishing/upload. |
| AUD-P2-001 | P2 | README and module documentation previously described legacy Edge/automatic publishing. | CLOSED — README and voice/captions module headers corrected at qualified HEAD `a5c57ca8f571980ca064c18e3c9672617c4a67ba`; manual draft-only Ryan route and explicit Edge rollback now documented. |
| AUD-P2-002 | P2 | M5 storyboard/retrieval/ranking guarantees rely heavily on workflow inline assertions rather than a dedicated regression test layer. | OPEN |
| AUD-P3-001 | P3 | Temporary M6.9 canary workflow remains after M6.9 closure. | REVIEW after audit evidence no longer depends on it |

## Confirmed safety state
- Production route remains committed-route driven.
- Publishing is disabled in the M6.9 route.
- Pre-M7 audit does not invoke `upload_agent.py` or any social/video upload action.
- Frozen storyboard branch has not been modified.
- Frozen Ryan/Qwen identity/quality parameters have not been modified.

## Current checkpoint
- Formal PRE-M7 audit result: **PASS — 10/10 Gates**; all direct P0/P1 blockers CLOSED and exact final executable qualification verified.
- Latest independently verified exact-SHA-qualified executable/config/test revision: `65bad44978d7b2a4f3509eb21ef48c760bf3ab9b`.
- M6 Qualification run `40004314075`, job `120588205873`: SUCCESS, 224 passed / 1 skipped; canonical locked production installation, `pip check`, and focused Gate10 Ryan-route regression PASS.
- Same run `40004314075`, Gate10 real clean-room E2E job `120589521499`: SUCCESS. Fresh exact-SHA checkout, empty output, real RSS/topic research + Gemini script, validated Qwen3 Ryan WAV + WhisperX alignment + canonical timeline, storyboard, real Pexels visual retrieval/ranking, captions, 11-scene 1080x1920 30fps MP4 render, M5.5 QC PASS, provenance-bound production package PASS. `REAL_NONPUBLISHING_CLEANROOM` exact SHA PASS, `media_uploaded=false`, `published=false`.
- P0 open: 0. P1 open: 0; all nine AUD-P1-001..009 CLOSED. P2/P3 retained items are documented separately and are not unresolved correctness/safety blockers.
- Current tracked inventory: 115/115 classified, UNKNOWN=0. Current first-party executable/config/test/workflow inventory: 74/74 differentially audited. The Gate10 change modified two existing runtime-significant blobs and no tracked paths were added/deleted/renamed.
- Frozen storyboard SHA: `ddd55af7ed3f7bd418b078140909750d758519bb` unchanged. Frozen Ryan/Qwen identity/quality parameters unchanged. No publishing/video upload, paid services, billing, or new secrets. Gate10 workflow has contents:read only and no media artifact upload.
- GLOBAL_MUTATION_CAPABILITY: AVAILABLE; GitHub Contents writes and exact blob read-back verified. Future invocations: drift-only verification; do not re-run clean-room E2E or change frozen production parameters absent relevant drift.
## Closure checkpoint — 2026-10-03
- Live active HEAD: `36357bd5c9e6f378d7fd167977f3dea86a4f58da`.
- Frozen `factory-v1-storyboard`: `ddd55af7ed3f7bd418b078140909750d758519bb`; unchanged.
- P0 open: 0.
- Fixed awaiting exact-SHA qualification: AUD-P1-001, AUD-P1-002, AUD-P1-008.
- READY_TO_FIX: AUD-P1-004 uploader explicit default-deny authorization; Gate 6 qualification watched-path/commit-message blind spots.
- OPEN/DESIGN_READY: AUD-P1-003 cross-run anti-repeat persistence; M5.4 visual-contract regression; production artifact provenance/run binding.
- Exact-SHA qualification for the current executable HEAD is still required before fixed P1 findings can close.

### Fix queue
1. AUD-P1-004 — add explicit human authorization gate before artifact discovery, credentials, API client creation, or network/upload activity; add negative tests proving no credential/network access without authorization. Preserve publishing disabled in normal audit/qualification paths.
2. Gate 6 qualification hardening — include all production-critical M6/script/storyboard/visual/dependency paths and execute meaningful M6.9 regression on every relevant push rather than commit-message matching; prove exact triggering SHA.
3. AUD-P1-003 — persist anti-repeat state across Actions runs using a read-only-safe cache/state mechanism; add restored-state and empty-state tests.
4. Visual contract — restore validated Source Card and controlled still-motion behavior while preserving current M6.9 voice/media resolver; add fail-closed acquisition-boundary and runtime tests.
5. Provenance contract — bind production-critical artifacts to explicit run identity/producer/schema; reject stale/wrong-producer/restored-cache contamination with adversarial tests.


## Closure checkpoint — 2026-10-04
- Repository tree inventory completed against current audit baseline: 106/106 tracked blobs classified; UNKNOWN=0. Classification: 77 ACTIVE, 25 REQUIRED, 4 TEMPORARY. Gate 1 evidence is complete subject to revalidation after subsequent mutations.
- P0 open: 0.
- AUD-P1-001 / AUD-P1-002 / AUD-P1-008 remain EXACT_SHA_PENDING because no workflow run is associated with the current executable HEAD; historical green runs do not qualify newer code.
- AUD-P1-004 is READY_TO_FIX on `agents/upload_agent.py@3a2a95daf84d1fe28aa363c30a57e07d0063e390`: root cause is an independently executable upload path with public default and no explicit authorization before artifact discovery/OAuth/network. Minimal fix: default private plus explicit default-deny authorization as the first operation in `main()`; negative regression must prove artifact discovery, credentials and network are untouched when unauthorized.
- AUD-P1-003 is DESIGN_READY: canonical state path exists, but Actions does not persist anti-repeat state across runners and corrupted/unreadable state currently degrades to empty history. Remediation must persist state without contents:write and fail closed on corrupted restored state.
- Visual-contract P1 is READY_TO_FIX: current `video_agent.py` lacks validated M5.4 Source Card helpers and controlled still-motion behavior while current `m54_smoke.py` calls those helpers. Restore the validated frozen M5.4 Source Card/motion implementation while preserving the current M6.9 voice/media resolver and Ryan/Qwen parameters.
- Gate 6 qualification hardening is READY_TO_FIX: qualification must watch the complete production-critical script/storyboard/visual/upload/dependency surface and run meaningful regression on every relevant push, not depend on commit-message matching.
- Gate 4 reproducibility remains open: runtime dependencies using unbounded/lower-bound-only constraints require a deterministic lock/constraints strategy or equivalent reproducibility evidence before Gate 4/10 PASS.
- Gate 8 normal draft workflow is manual/read-only/non-publishing, but independently executable `upload_agent.py` prevents Gate 8 PASS until AUD-P1-004 is closed.
- Frozen `factory-v1-storyboard` reference remains immutable; no publishing/OAuth/YouTube upload was invoked during audit work.

### Deterministic AUDIT_CURSOR
- tracked classified: 106/106; UNKNOWN=0
- executable/config audit denominator: 69
- next closure queue: AUD-P1-004 -> qualification hardening -> AUD-P1-003 -> visual contract -> provenance/data contract
- Gate 9 remains blocked until Gates 1–8 are evidenced; temporary canary/milestone evidence is retained.


## Closure execution checkpoint — 2026-10-04 write unblocked
- Supported GitHub Contents API write capability verified on `factory-v1-voice-m6`; repository connection reports push/admin permission. No low-level Git/ref bypass was used.
- AUD-P1-004 implementation committed: `610f72cb375e9172168d3b44ad7f216def823cb5`; uploader default is private and explicit publish authorization is the first operation in `main()`.
- AUD-P1-004 regression coverage committed and isolated from external API imports: `f0fe9b26637e194e116c11f92eb9940d3e09928c`.
- Qualification blind spot remediation committed: `518597e0ecf248428e06752f213231e43cbdf56e`. Relevant pushes now watch `agents/**`, `scripts/**`, `config/**`, `tests/**`, `requirements.txt`, and qualification/publish workflows; push qualification no longer depends on commit-message matching.
- Exact-SHA M6 Qualification run `37201974612` and M6.9 Ryan Production Canary run `37201974617` started for `518597e0ecf248428e06752f213231e43cbdf56e`; results pending at checkpoint time.
- Inventory evidence: classified 106/106, UNKNOWN=0 (Gate 1 PASS_READY pending final persisted/revalidation semantics).
- Executable/config semantic audit: 69/69 exact blobs audited at the pre-mutation checkpoint; affected mutated blobs require revalidation, so Gate 3 remains PASS_READY rather than PASS.
- Frozen `factory-v1-storyboard` remains `ddd55af7ed3f7bd418b078140909750d758519bb`; publishing/upload was not invoked.

## Closure-first gate dependency map — 2026-10-05
- Gate 1 — PASS. Evidence: tracked inventory 106/106 classified; UNKNOWN=0; active HEAD revalidated at `a65f7c69598f68868dce12f1efafb4079d2b53cb`. No unresolved P0/P1 directly blocks inventory completeness.
- Gate 3 — PASS_READY only. Static-audit denominator is 69, but the 2026-10-04 checkpoint explicitly requires revalidation of affected mutated executable/config blobs before PASS.
- AUD-P1-003 DIRECT_BLOCKS: Gate 5, Gate 6, Gate 7, Gate 10 — cross-run anti-repeat persistence/fail-closed restored state.
- AUD-P1-004 DIRECT_BLOCKS: Gate 8, Gate 10 — independent uploader authorization/default-deny boundary; live remediation/evidence must be synchronized before closure.
- Visual-contract P1 DIRECT_BLOCKS: Gate 5, Gate 7, Gate 10.
- Provenance/data-contract P1 DIRECT_BLOCKS: Gate 5, Gate 7, Gate 10.
- Qualification watched-path blind spot DIRECT_BLOCKS: Gate 6, Gate 7, Gate 10; remediation evidence must be synchronized from live repository/Actions state.


## Closure synchronization — 2026-10-06
- Live pre-write HEAD: `6e6fa82ccf17865167c39564b35536252538c31b`; changes after the latest qualified executable state are audit-docs-only.
- Latest exact-SHA-qualified executable: `a65f7c69598f68868dce12f1efafb4079d2b53cb`; M6 Qualification run `37205491751`, job `111445703429` SUCCESS.
- Gate 2 — PASS. Persisted architecture evidence: `PRE_M7_CLOSURE_EVIDENCE_GATE2.md@47b317ba3e63e2804bfa93fbe46b020c24d96600`. Actual chain: Topic/Research -> Script -> Voice Script/TTS -> Alignment -> canonical timeline -> Storyboard -> Visual retrieval/ranking -> Captions -> Render -> QC -> Production Package. No unresolved P0/P1 directly blocks architecture completeness.
- Gate 3 — PASS. First-party executable/config semantic audit: 69/69 exact blobs; differential revalidation evidence persisted in `PRE_M7_CLOSURE_EVIDENCE_GATE3_P1_004.md@0fedc90ecb0038414244255f3604abf25d9007db`. No executable/config drift after qualified executable SHA.
- Gate 8 — PASS. Uploader is default-private and explicit-authorized-only; audit/qualification/draft paths do not invoke publishing; no paid service, billing, or new secret was introduced for audit closure. AUD-P1-004 is CLOSED with exact-SHA qualification above.
- Finding dependency map remains scoped: AUD-P1-003 DIRECT_BLOCKS=[5,6,7,10]; visual-contract P1 DIRECT_BLOCKS=[5,7,10]; provenance/data-contract P1 DIRECT_BLOCKS=[5,7,10]. Qualification blind-spot remediation is contained in the qualified executable SHA; it does not block Gates 2/3/8.
- Inventory remains classified 106/106, UNKNOWN=0. Executable/config audit remains 69/69.
- Safety invariants preserved: `factory-v1-storyboard` unchanged at `ddd55af7ed3f7bd418b078140909750d758519bb`; no publishing/upload invoked; frozen Ryan/Qwen identity/quality parameters unchanged.


## Closure synchronization — 2026-10-15
- Live active HEAD: `0ded47e7d44e212b912d346d6f8e1ecaa856c6ad`; no executable/config drift since the previously verified differential checkpoint.
- Latest exact-SHA-qualified executable remains `a65f7c69598f68868dce12f1efafb4079d2b53cb`; M6 Qualification run `37205491751`, job `111445703429` SUCCESS.
- AUD-P1-002 is CLOSED: implementation `22626f8b` plus regression tests `36357bd5` are ancestors of the qualified executable SHA, the qualifying suite executed the state-contract tests, and no later executable drift invalidates the fix.
- Current tracked inventory accounting: 112/112 classified; UNKNOWN=0. Gate 1 remains PASS.
- Current first-party executable/config/runtime-significant accounting: 70/70 exact blobs audited, including the dependency-control constraints file. Gate 3 remains PASS.
- P0 open: 0.
- Safety invariants preserved: `factory-v1-storyboard` remains frozen; publishing/upload was not invoked; frozen Ryan/Qwen identity/quality parameters are unchanged.


## Gate 4 closure synchronization — 2026-10-15
- Pre-ledger live HEAD: `ec3f93b5478cadb8a0fe52396fd22dcd75d95aa3`; this and the ledger synchronization are docs-only descendants of the qualified executable/config SHA.
- Latest exact-SHA-qualified executable/config revision: `0fdea313c8446d2112859d4fd5420e6e3b31ffcd`.
- M6 Qualification run `38703875490`, job `116318345733`: SUCCESS; `128 passed, 1 skipped`; `pip check` PASS; CPython 3.11.17; ubuntu-24.04.
- Gate 4 — PASS. Closure evidence: `PRE_M7_GATE4_REPRODUCIBILITY_CLOSURE.md@9de629eb6a2eb9e3cd1e4b5a9c24baed7851f357`.
- Canonical shared production dependency lock: `constraints/m6-qualification.txt@b18072acbb3fbb7d282b6bf4516a112c8a1dfe65`, 189 exact-pinned packages derived from a successful exact-SHA environment.
- Qualification workflow: `.github/workflows/m6-qualification.yml@856c68ff07bb21fa3a1b7363aa0788c91de07235`; watches `constraints/**`, installs full production requirements through the lock, performs `pip check`, and executes dependency-contract regression.
- Draft workflow: `.github/workflows/publish.yml@32a9a402f0c740c781820e44d3811a2d02bed70b`; same lock, same Python 3.11.17, ubuntu-24.04, runtime identity recording. Publishing remains disabled/uninvoked.
- Focused regression: `tests/test_pre_m7_dependency_contracts.py@715c33746ba2e393dca679b9db4bf398b60b8f80`; executed by the successful final qualification.
- AUD-P1-001 — CLOSED on the evidence above.
- Current tracked inventory accounting: 113/113 classified; UNKNOWN=0. The only new tracked path since the 112/112 checkpoint is the dependency-contract regression test, classified REQUIRED/TEST. Gate 1 remains PASS.
- Current first-party executable/config/test/runtime-significant accounting: 71/71 exact blobs audited. The new dependency-contract regression adds one denominator entry; modified workflow/lock blobs were differentially audited and exact-SHA-qualified. Gate 3 remains PASS.
- Hosted runner image patch revisions and Ubuntu apt/ffmpeg contents remain provider-managed boundaries; exact observed identities are recorded, and correctness is fail-closed through locked install, `pip check`, tests, renderer/QC gates. No paid service, billing action, new secret, upload, or publishing action was introduced.

### AUDIT_CURSOR delta
- `constraints/m6-qualification.txt|b18072acbb3fbb7d282b6bf4516a112c8a1dfe65|REQUIRED_CONFIG|canonical production dependency lock|qualified environment|qualification+draft workflows|runtime/config=yes|QUALIFIED|AUD-P1-001`
- `.github/workflows/m6-qualification.yml|856c68ff07bb21fa3a1b7363aa0788c91de07235|ACTIVE_WORKFLOW|exact-SHA qualification and dependency enforcement|GitHub Actions|tests+production lock|workflow=yes|QUALIFIED|AUD-P1-001`
- `.github/workflows/publish.yml|32a9a402f0c740c781820e44d3811a2d02bed70b|ACTIVE_WORKFLOW|manual non-publishing draft generation|GitHub Actions|production agents+lock|workflow=yes|QUALIFIED_STATIC_CONTRACT|AUD-P1-001`
- `tests/test_pre_m7_dependency_contracts.py|715c33746ba2e393dca679b9db4bf398b60b8f80|REQUIRED_TEST|dependency/workflow reproducibility regression|pytest|qualification workflow|test=yes|QUALIFIED|AUD-P1-001`

Safety invariants unchanged: frozen storyboard `ddd55af7ed3f7bd418b078140909750d758519bb`; frozen Ryan/Qwen identity unchanged; no publishing/upload invoked.


## Closure synchronization — 2026-10-23
- Exact qualifying executable HEAD: `7e898c57108966d0e4c81e07a218d1a681104a88`; M6 Qualification `39925089835`, job `120319389641`: SUCCESS, 140 passed / 1 skipped, full locked production install and `pip check` PASS.
- AUD-P1-003 CLOSED after implementation and focused tests were both executed on that exact SHA. Prior intermediate test-only failure `39924728555` was caused by a double-escaped newline in a workflow assertion; corrected at `7e898c57` without weakening the test.
- Changed runtime-significant blobs: `.github/workflows/publish.yml@09ee25fae9f895484d295abd084d4b6c0c29628d`, `agents/script_agent.py@ff9bdaf2632776ac580fb1b7e04e06098bc778ee`, `tests/test_pre_m7_state_contracts.py@6e52e96b5e4a9375e5d57fc0339669256d5b4d33`. All differentially inspected and exact-SHA qualified; no tracked file additions/deletions.
- Current tracked inventory: 113/113, UNKNOWN=0. Current first-party executable/config/test/workflow denominator: 71/71. Gates 1 and 3 remain PASS; Gate 4 and Gate 8 remain PASS with no affected criteria.
- Gates 5/7/10 remain directly blocked by the existing visual and provenance contracts. Gate 6 remains IN_PROGRESS pending explicit watched-path/enforcement regression and complete workflow-closure evidence; do not treat unrelated P1 as a Gate 6 blocker.
- Global mutation capability: AVAILABLE (four supported Contents writes plus read-back verification in this session). Frozen `factory-v1-storyboard` remains `ddd55af7ed3f7bd418b078140909750d758519bb`; no video publishing/upload, new secrets, paid services, or Ryan/Qwen parameter changes.


## Gate 6 closure synchronization — 2026-10-23
- Gate 6 formally PASS: all three tracked workflows accounted for; production-critical push watch covers `agents/**`, `scripts/**`, `config/**`, `tests/**`, `requirements.txt`, `constraints/**`, the benchmark corpus, and each tracked workflow. M6.9/push qualification runs the full test directory without commit-message filtering, checks exact triggering SHA, and has contents:read permissions.
- AUD-P1-007 CLOSED with regression and exact-SHA evidence: executable/config/test SHA `f85a8729c3c730d16f693ef4f134365966846353`; M6 Qualification run `39925566753`, job `120320966484` SUCCESS, 144 passed / 1 skipped. Prior M6.9 qualification `39925089835` SUCCESS, 140 passed / 1 skipped, closed AUD-P1-003.
- Modified blobs: `.github/workflows/m6-qualification.yml@f6bc535beabd9718add211c705c02306dd3971f6` and `tests/test_pre_m7_dependency_contracts.py@b60b3e5852b59e4d524d28a96c3d47b67acdcf00`; both differentially audited. No tracked paths added/deleted: inventory 113/113, UNKNOWN=0; executable/config/test/workflow 71/71. Gates 1/3 remain PASS.
- Gates PASS: 1,2,3,4,6,8 = 6/10. Gates 5/7/10 remain directly blocked by AUD-P1-005 and AUD-P1-006; Gate 9 awaits Gates 1–8. The M6.9 canary uses synthetic visual fixtures and is not accepted as clean-room production E2E evidence.
- Safety: frozen storyboard SHA `ddd55af7ed3f7bd418b078140909750d758519bb` unchanged; no publishing entry point invoked, no paid services/new secrets, no Ryan/Qwen identity or quality changes.


## Visual-contract closure synchronization — 2026-10-23
- Live executable HEAD: `0ad2953c45e81ca31e08d86107804390d7400245`; latest exact-SHA-qualified executable is the same SHA. M6 Qualification `39932656805`, job `120344462909`: SUCCESS, 160 passed / 1 skipped; exact triggering SHA verified; locked production dependency install and `pip check` PASS.
- AUD-P1-005 CLOSED: restored M5.4 mandatory Source Card and caption-safe still-motion renderer from frozen reference without modifying the frozen branch, preserving the fail-closed M6.9 voice artifact resolver. `agents/video_agent.py@389e440c280984824956229cd2b62db6e5677fd2`; focused positive/negative regression `tests/test_pre_m7_visual_contracts.py@41386c5b3c430cc99b1510b799ad9f89779958d8`, executed by the qualifying push run.
- Current tracked tree 114/114 classified, UNKNOWN=0 (one new REQUIRED_TEST path). Executable/config/test/workflow inventory 72/72 exact blobs audited (one new test; renderer changed and differentially audited). Gates 1 and 3 remain PASS; unaffected Gates 2,4,6,8 remain PASS. Formal total 6/10.
- P0 open: 0. Remaining P1: AUD-P1-006 DESIGN_READY, DIRECT_BLOCKS=[5,7,10]. Gates 5 and 7 IN_PROGRESS; Gate 9 awaits Gates 1–8; Gate 10 NOT_STARTED. Do not claim synthetic fixture tests or intermediate canary as clean-room E2E.
- Frozen `factory-v1-storyboard` unchanged at `ddd55af7ed3f7bd418b078140909750d758519bb`. No publishing/upload, new secrets, paid services, or frozen Ryan/Qwen identity changes.

### AUDIT_CURSOR delta — visual contract
- `agents/video_agent.py|389e440c280984824956229cd2b62db6e5677fd2|ACTIVE_RUNTIME|Source Card/still motion/M6.9 voice resolver|asset manifest+voice|renderer manifest+final MP4|runtime=yes|QUALIFIED|AUD-P1-005,AUD-P1-006`
- `tests/test_pre_m7_visual_contracts.py|41386c5b3c430cc99b1510b799ad9f89779958d8|REQUIRED_TEST|visual source-card/motion fail-closed regression|pytest|M6 Qualification|test=yes|QUALIFIED|AUD-P1-005`


## Run-bound selection qualification checkpoint — 2026-10-23
- Executable/config/test HEAD: `058d13067fab1a4792de1336aa2becc7a8f40d2a`; M6 Qualification run `39939650583`, job `120367642155`: SUCCESS; 176 passed / 1 skipped, full production constraints installation and `pip check` PASS. The run executed `tests/test_pre_m7_run_provenance.py` on the exact triggering SHA.
- AUD-P1-006 partial direct-blocker remediation: the production draft workflow now exports the unique script timestamp to `FACTORY_RUN_TIMESTAMP`; script, narration, storyboard, visual retrieval, renderer and QC consumers select exact run-bound filenames rather than lexicographically latest artifacts. Missing/malformed identity or missing exact artifact fails closed under GitHub Actions. Local-only unbound discovery remains for interactive backward compatibility, not production qualification.
- Newly added runtime/test paths: `scripts/m6_run_provenance.py@0beac1324fe7a885c8c6622d3715f84d718d24c4` and `tests/test_pre_m7_run_provenance.py@decc42187cf03073e342ff95f77521a4a94e4be9`. Modified and differentially audited: `agents/voice_agent.py@9a77f9e34a9e85aa89d35897bbab587e5d8c80e2`, `agents/captions_agent.py@734064c47359568d83773ebfa54f2aa601eee863`, `agents/storyboard_agent.py@83c3b6a888a7c18e1a2e76355896a895ddffe9f3`, `agents/visuals_agent.py@efcffe76965e67de033b2ef69acc9ee56a295753`, `agents/video_agent.py@953af875127e643403eba426d01f65af48b7edb4`, `agents/qc_agent.py@49fb35c2d4c00bc2e2942c19c57762548795f0e9`, `.github/workflows/publish.yml@34fe315d68a4773a5c2938ef53afc7abd56a470e`.
- Dynamic Gate 1 inventory: 116/116 classified, UNKNOWN=0 (114 + one REQUIRED_RUNTIME and one REQUIRED_TEST). Dynamic Gate 3 first-party executable/config/test/workflow audit: 74/74 exact blobs (72 + two new runtime/test paths; changed existing blobs differentially audited). Gates 1 and 3 remain PASS.
- Formal Gates PASS: 1,2,3,4,6,8 = 6/10; delta PASS=0. AUD-P1-006 remains READY_TO_FIX, DIRECT_BLOCKS=[5,7,10] because producer/schema/source-hash provenance and restored-cache contamination rejection are not yet fully enforced. Gates 5/7 remain IN_PROGRESS; Gate 9 awaits Gates 1–8, Gate 10 awaits clean-room E2E. P0 open=0; P1 CLOSED=7, READY_TO_FIX=1.
- GLOBAL_MUTATION_CAPABILITY=AVAILABLE: supported GitHub Contents writes succeeded, no safety/tool-layer write refusal. Frozen storyboard remains `ddd55af7ed3f7bd418b078140909750d758519bb`; no publishing/upload, paid service, new secret, or Ryan/Qwen identity/quality change. The M6.9 fixture canary is not accepted as full production E2E.

### AUDIT_CURSOR delta — run-bound selection
- `scripts/m6_run_provenance.py|0beac1324fe7a885c8c6622d3715f84d718d24c4|REQUIRED_RUNTIME|fail-closed active-run artifact selection|draft workflow run stamp|all critical artifact consumers|runtime=yes|QUALIFIED|AUD-P1-006`
- `tests/test_pre_m7_run_provenance.py|decc42187cf03073e342ff95f77521a4a94e4be9|REQUIRED_TEST|wrong-run/missing/invalid Actions identity regressions|pytest|M6 Qualification|test=yes|QUALIFIED|AUD-P1-006`
- `agents/voice_agent.py|9a77f9e34a9e85aa89d35897bbab587e5d8c80e2|ACTIVE_RUNTIME|exact script selection|script artifact|narration timeline|runtime=yes|QUALIFIED|AUD-P1-006`
- `agents/captions_agent.py|734064c47359568d83773ebfa54f2aa601eee863|ACTIVE_RUNTIME|exact timeline selection|narration timeline|captions|runtime=yes|QUALIFIED|AUD-P1-006`
- `agents/storyboard_agent.py|83c3b6a888a7c18e1a2e76355896a895ddffe9f3|ACTIVE_RUNTIME|exact timeline selection|narration timeline|storyboard|runtime=yes|QUALIFIED|AUD-P1-006`
- `agents/visuals_agent.py|efcffe76965e67de033b2ef69acc9ee56a295753|ACTIVE_RUNTIME|exact storyboard selection|storyboard|retrieval and ranking|runtime=yes|QUALIFIED|AUD-P1-006`
- `agents/video_agent.py|953af875127e643403eba426d01f65af48b7edb4|ACTIVE_RUNTIME|exact script selection preserving M6.9 resolver|script+assets+voice|renderer|runtime=yes|QUALIFIED|AUD-P1-006`
- `agents/qc_agent.py|49fb35c2d4c00bc2e2942c19c57762548795f0e9|ACTIVE_RUNTIME|exact script selection|production artifacts|QC report|runtime=yes|QUALIFIED|AUD-P1-006`
- `.github/workflows/publish.yml|34fe315d68a4773a5c2938ef53afc7abd56a470e|ACTIVE_WORKFLOW|export unique active-run timestamp|script generation|downstream draft steps|workflow=yes|QUALIFIED_STATIC_CONTRACT|AUD-P1-006`


## Closure-first execution checkpoint — 2026-10-23 script provenance hardening
- Active HEAD before documentation sync: `bc1d19f5fbf82da05433a87603a21955b76e993f`. Frozen `factory-v1-storyboard` remains `ddd55af7ed3f7bd418b078140909750d758519bb`.
- AUD-P1-006 remains READY_TO_FIX and DIRECT_BLOCKS=[5,7,10]. Coherent first-boundary remediation committed (not yet CLOSED): `agents/script_agent.py@e314155be10ca2bd42d14cd5e28bed9df7bd9f74` stamps script producer/schema/run identity and canonical payload SHA-256; `scripts/m6_run_provenance.py@96ace277b7cb7375d3672f5862d605e8af7d746d` rejects wrong producer/schema/run, malformed JSON, missing fields, and modified payload before TTS selection; `tests/test_pre_m7_run_provenance.py@592f40fdb91bfe8c5fafdb8e880619f94c2a4e01` adds adversarial wrong-producer/schema/run, restored-cache tamper, missing-digest, and corrupt-JSON tests. Existing Ryan/Qwen identity, parameters, publishing authorization, and frozen storyboard are untouched.
- Implementation commits in sequence: `806faac1055f0e6399f6752b594f9f8d1bc2f5aa`, `dcc6b11ca8671cf9b8352fc421b0bfdac3ea1026`, `bc1d19f5fbf82da05433a87603a21955b76e993f`. GitHub Contents writes and read-back succeeded: GLOBAL_MUTATION_CAPABILITY=AVAILABLE. These sequential commits are connector-forced intermediate states; only final executable SHA `bc1d19f5fbf82da05433a87603a21955b76e993f` is eligible for new qualification.
- EXACT_SHA_PENDING: new Actions M6 Qualification for `bc1d19f5fbf82da05433a87603a21955b76e993f` has not been verified. The connector's commit-workflow-runs endpoint exposes only PR-triggered runs and returns zero even for previously verified successful push SHA `058d13067fab1a4792de1336aa2becc7a8f40d2a`; therefore absence of results is NOT evidence of a failed or absent push run. Do not claim qualification or P1 closure until exact run/job/steps are verified.
- Dynamic tracked denominator unchanged: 116/116 classified, UNKNOWN=0. Executable/config/test/workflow denominator unchanged: 74/74; the three changed exact blobs above were differentially inspected. Gates PASS remain 1,2,3,4,6,8 = 6/10; delta PASS=0; P0 open=0; P1 CLOSED=7, READY_TO_FIX=1; delta CLOSED=0. No fixture canary is counted as clean-room E2E.
- Next priority: obtain and inspect push-triggered M6 Qualification on exact SHA `bc1d19f5fbf82da05433a87603a21955b76e993f`; fix CI failure if any, then extend AUD-P1-006 producer/schema/source-hash checks across narration timeline -> storyboard -> candidates/assets -> renderer/QC, with focused adversarial regressions before Gate5/Gate7 closure. No unrelated discovery.
### AUDIT_CURSOR delta — script provenance
- `agents/script_agent.py|e314155be10ca2bd42d14cd5e28bed9df7bd9f74|ACTIVE_RUNTIME|stamp script producer/schema/run and canonical payload digest|RSS/Gemini script generation|voice_agent|runtime=yes|EXACT_SHA_PENDING|AUD-P1-006`
- `scripts/m6_run_provenance.py|96ace277b7cb7375d3672f5862d605e8af7d746d|REQUIRED_RUNTIME|reject mismatched script producer/schema/run/content before TTS|script JSON|all select_run_artifact consumers|runtime=yes|EXACT_SHA_PENDING|AUD-P1-006`
- `tests/test_pre_m7_run_provenance.py|592f40fdb91bfe8c5fafdb8e880619f94c2a4e01|REQUIRED_TEST|adversarial producer/schema/run/restored-cache corruption tests|pytest|M6 Qualification|test=yes|EXACT_SHA_PENDING|AUD-P1-006`


## Exact-SHA provenance qualification — 2026-10-23
- Current qualifying executable/config/test SHA: `6bc586cde6ba197b3ddefbf76df5980674e1edf4`; M6 Qualification run `39954158582`, job `120415699911` SUCCESS, `196 passed, 1 skipped`, locked production install and `pip check` PASS. The full `tests/` directory, including new source-integrity adversarial tests, ran on this exact SHA. Previous script-only SHA `bc1d19f5fbf82da05433a87603a21955b76e993f` independently qualified via run `39946336936`, job `120389811312` SUCCESS, `182 passed, 1 skipped`.
- AUD-P1-006 remains READY_TO_FIX and DIRECT_BLOCKS=[5,7,10]. Qualified subfixes now enforce producer/schema/run/payload SHA-256 for script and exact upstream byte SHA-256 for narration timeline and storyboard. Wrong producer, wrong schema, wrong run, tampered content, changed upstream source, missing upstream, and restored-cache substitution fail closed in bound Actions selection. Remaining direct blocker: extend equivalent run-bound producer/schema/source-hash validation across ranked candidate/asset manifests, renderer and final QC/package consumers; current subfix is NOT full finding closure.
- Coherent Contents writes, all verified by read-back: `scripts/m6_run_provenance.py@477100a93ce13b362579d01e23bd232f5c8f6b20` (`d2ad7dec`); `agents/voice_agent.py@83f5ccc28d6fb68793ae9f2c28ed6e188ff95714` (`09ee6bac`); `agents/storyboard_agent.py@fec1cfd2904f2f840ad0585ffb70c5a57e3976ed` (`55183a30`); `tests/test_pre_m7_run_provenance.py@e581ecdd04868406126adba2f95d84b8f32d090b` (`6bc586cd`). Earlier script-provenance blobs `agents/script_agent.py@e314155be10ca2bd42d14cd5e28bed9df7bd9f74` and `scripts/m6_run_provenance.py@96ace277b7cb7375d3672f5862d605e8af7d746d` were included in the successful qualification ancestry.
- Dynamic tracked inventory unchanged: 116/116 classified, UNKNOWN=0. Executable/config/test/workflow audited 74/74; four changed existing runtime/test blobs differentially inspected and exact-SHA qualified. Gates PASS remain 1,2,3,4,6,8 = 6/10; delta PASS=0. P0 open=0; P1 CLOSED=7, READY_TO_FIX=1; delta CLOSED=0. GLOBAL_MUTATION_CAPABILITY=AVAILABLE, no global safety/tool-layer write refusal. No canary fixture is treated as production E2E.
- Frozen `factory-v1-storyboard` remains `ddd55af7ed3f7bd418b078140909750d758519bb`; Ryan/Qwen frozen identity and quality parameters unchanged. No publishing/upload, paid services, billing or new secrets.

### AUDIT_CURSOR differential — source-bound narration/storyboard
- `agents/script_agent.py|e314155be10ca2bd42d14cd5e28bed9df7bd9f74|ACTIVE_RUNTIME|stamp script producer/schema/run/content digest|script generation|voice agent|runtime=yes|QUALIFIED|AUD-P1-006`
- `scripts/m6_run_provenance.py|477100a93ce13b362579d01e23bd232f5c8f6b20|REQUIRED_RUNTIME|verify script/timeline/storyboard provenance and upstream SHA-256|bound artifacts|voice/storyboard/visuals|runtime=yes|QUALIFIED|AUD-P1-006`
- `agents/voice_agent.py|83f5ccc28d6fb68793ae9f2c28ed6e188ff95714|ACTIVE_RUNTIME|stamp timeline exact source-script SHA-256|script artifact|storyboard/captions|runtime=yes|QUALIFIED|AUD-P1-006`
- `agents/storyboard_agent.py|fec1cfd2904f2f840ad0585ffb70c5a57e3976ed|ACTIVE_RUNTIME|stamp storyboard exact timeline SHA-256|narration timeline|ranked visual retrieval|runtime=yes|QUALIFIED|AUD-P1-006`
- `tests/test_pre_m7_run_provenance.py|e581ecdd04868406126adba2f95d84b8f32d090b|REQUIRED_TEST|wrong producer/schema/run/payload/upstream/restored-cache adversarial tests|pytest|M6 Qualification|test=yes|QUALIFIED|AUD-P1-006`

## AUD-P1-006 closure and Gate5/Gate7 synchronization — 2026-10-23
- Qualified executable/config/test SHA: `747adc016cab245959d4e3e45d427d1ea67e09a2`. Exact-SHA M6 Qualification run `39961880015`, job `120441632589`: SUCCESS, 221 passed / 1 skipped, locked full production dependency install, `pip check` PASS. The full `tests/` suite including `tests/test_pre_m7_run_provenance.py` ran on this SHA.
- AUD-P1-006 CLOSED: existing qualified script/timeline/storyboard provenance now extends through M5.3 ranked candidates, selected media bytes, M5.4 renderer/final MP4, M5.5 QC and production package. Every critical JSON artifact has producer, schema, exact run timestamp, canonical payload digest and expected upstream source-byte hashes. Asset paths are constrained to the active-run output directory; voice WAV/MP3 remains exclusively resolved by the frozen M6.9 media resolver. No publishing/OAuth action was invoked.
- Positive/negative/adversarial regression proves wrong producer/schema/run, corrupt or tampered manifests, stale upstream storyboard, modified downloaded media, modified voice/captions/final MP4, altered renderer/QC/visual-selection reports, path traversal and restored-cache contamination fail closed. Earlier intermediate qualification `39961843368` failed a test-assertion defect (invalid JSON fixture when testing a digest mismatch); corrected test retained the stronger digest assertion and final exact SHA passed. No valid QC/safety assertion was weakened.
- Gate 5 PASS: direct blocker AUD-P1-006 closed; actual producer/consumer source integrity is enforced in draft rendering, QC and package verification. Gate 7 PASS: focused positive/negative/adversarial coverage and full exact-SHA regression passed, with previously validated M6.9 media/QC route retained. Fixture tests do NOT prove the full real Topic-to-Package chain; this remains explicitly Gate 10.
- Gate 9 is now actionable only after Gates 1–8 PASS: cleanup must preserve every still-referenced evidence file and frozen production route. Gate 10 requires clean checkout, no stale state, no publishing/paid services, actual end-to-end source and media chain, and exact final executable SHA.
- Dynamic Gate 1: 116/116 tracked classified, UNKNOWN=0. Dynamic Gate 3: 74/74 first-party executable/config/test/workflow blobs audited. Changed existing blobs only; no denominator change. Formal PASS=8/10; P0 open=0; P1 open=0.
- GLOBAL_MUTATION_CAPABILITY=AVAILABLE: supported GitHub Contents writes and exact blob/commit read-back succeeded; no safety/tool-layer refusal. Frozen `factory-v1-storyboard` remains `ddd55af7ed3f7bd418b078140909750d758519bb`. Ryan/Qwen identity/quality parameters untouched. No video publishing/upload, new secrets, billing or paid services.

### AUDIT_CURSOR differential — visual/render/QC provenance
- `scripts/m6_run_provenance.py|f6ae43a31f5c5bfdc2c0a44e08ba56cc0e07eaab|REQUIRED_RUNTIME|exact-run script/storyboard/candidates/media/renderer/QC source-hash verification|producer artifacts|renderer+QC+package|runtime=yes|QUALIFIED|AUD-P1-006`
- `agents/visuals_m53_agent.py|10c00c84025a3a74c1f8ad24376341e92f75e755|ACTIVE_RUNTIME|stamp M5.3 candidate and asset manifests with exact upstream media|storyboard+ranked retrieval|renderer+QC|runtime=yes|QUALIFIED|AUD-P1-006`
- `agents/video_agent.py|b99c1736545488b1b2548da97461d9e568b0c196|ACTIVE_RUNTIME|verify visual provenance before rendering; stamp renderer after final MP4|visuals+voice+captions|QC+package|runtime=yes|QUALIFIED|AUD-P1-006`
- `agents/qc_agent.py|cb3e9aa43c6e515873cb542f80bd3d37fa73dcc9|ACTIVE_RUNTIME|verify renderer/media; stamp QC report with final media and visual QC evidence|renderer+final+visual QC|package gate|runtime=yes|QUALIFIED|AUD-P1-006`
- `scripts/m6_production_package_gate.py|d65191b5d604311ee117fc7cc104db609c4b46af|REQUIRED_RUNTIME|verify bound QC/package when active-run timestamp exported|QC+renderer+media|production package|runtime=yes|QUALIFIED|AUD-P1-006`
- `tests/test_pre_m7_run_provenance.py|8765db131542599361cc3aefe7fc3f1d7740b9ec|REQUIRED_TEST|positive+adversarial visual/render/QC provenance and package regressions|synthetic fixture contracts|M6 Qualification|test=yes|QUALIFIED|AUD-P1-006`


## Gate 9 controlled-cleanup closure — 2026-10-23
- Gate 9 formally PASS after Gates 1–8 PASS. Live HEAD before ledger-only closure: `a5c57ca8f571980ca064c18e3c9672617c4a67ba`. Frozen storyboard SHA `ddd55af7ed3f7bd418b078140909750d758519bb` unchanged.
- Cleanup commits: `5d31ed4c`, `eb835b1c`, `39e05b77` corrected README and voice/captions documentation that incorrectly described automatic publication or Edge as the default; `188f69d6` removed only obsolete `docs/audit/PRE_M7_CLOSURE_ACCUMULATOR_2026-10-06.md` after synchronization of its Gate 2/3/8 and AUD-P1-004 closure evidence into this primary ledger. Existing Gate 2/3 evidence documents and Gate 4 reproducibility evidence remain retained; no still-referenced evidence was deleted.
- Reference/consumer proof: complete GitHub tracked tree at `a5c57ca8` is nontruncated, 115 blobs; the deleted accumulator is absent. All three workflow files were read at their current blobs: none references the deleted accumulator. The Ryan fixture canary is intentionally retained because `.github/workflows/m6-qualification.yml` watches it and the README identifies it as temporary/fixture-only. No removal of this active workflow is needed for Gate 9, and it must never be treated as real E2E evidence.
- Additional safety cleanup: `.github/workflows/publish.yml@45853b62c28bb1362cdb0cbf1242d2981d06a07b` exports JSON/Markdown QC metadata only (not MP4/WAV/MP3); `.github/workflows/m6-9-production-canary.yml@050b4958e4460853c3a0ca4e693a80211b1bd676` likewise exports JSON/Markdown only. Canary uses exact-SHA checkout, locked production dependencies, fixed Python/runner identity and regression checks; synthetic visual fixtures remain explicitly marked as fixtures.
- Exact-SHA M6 Qualification run `39963686148`, job `120447883488`: SUCCESS on `a5c57ca8f571980ca064c18e3c9672617c4a67ba`, 222 passed / 1 skipped, locked production dependency install and `pip check` PASS. M6.9 fixture canary run `39963686087`, job `120447883505`: SUCCESS on the same SHA. Neither is accepted as Gate 10 real clean-room E2E.
- Dynamic Gate 1 denominator: 115/115 tracked blobs classified, UNKNOWN=0 (116 minus one deleted accumulator). Gate 3 denominator: 74/74 executable/config/test/workflow paths audited; changed existing workflow and regression blobs were differentially reviewed and exact-SHA qualified, with no new runtime-significant path. Gates 1 and 3 retain PASS. P0 open=0; P1 open=0, all eight CLOSED; AUD-P2-001 CLOSED, AUD-P2-002 remains OPEN, AUD-P3-001 remains retained-for-reference.
- GLOBAL_MUTATION_CAPABILITY=AVAILABLE on successful supported Contents write and read-back. Gate 10 remains NOT_STARTED: it requires a genuinely fresh clean checkout and real Topic→Research→Script→Ryan TTS→WhisperX alignment→canonical timeline→storyboard→real visual retrieval/ranking→captions→1080x1920 30fps render→QC→package, without publishing, media upload, paid services, new secrets, or stale-state fixtures. A green fixture canary does not satisfy this criterion.

## FINAL PASS — Gate10 real clean-room closure — 2026-10-23
- Pre-fix executable/config/test HEAD `a348f855d375e493d15c56ab7ff74c467a0dc3b3`: M6 Qualification run `39995922627` job `120559296683` SUCCESS, but real E2E job `120560440978` FAILED at final assertion `MISSING_REAL_STAGE:m6_alignment`. Root cause from live job log: `agents/voice_agent.py` selected `Backend: edge`, because the Gate10 preflight checked the committed `m6-ryan` route but did not export `FACTORY_VOICE_BACKEND` to the following steps. This was a workflow propagation defect, not a Ryan/Qwen model or alignment defect; no production identity/quality parameters were changed.
- Corrected existing workflow blob `.github/workflows/m6-qualification.yml@eda36200b5a4ed113abd1f7b5d6c7446450b271b` and added focused regression in existing `tests/test_pre_m7_dependency_contracts.py@42852567756895ef861861ea7d7adac4a5bf77ac`. The regression asserts validated Ryan backend is exported via `GITHUB_ENV` before real voice generation; it would fail on the prior workflow. Both changed blobs are differentially audited. No tracked file was added, deleted or renamed; Gate1=115/115 UNKNOWN=0 and Gate3=74/74 remain PASS.
- Final exact executable/config/test SHA: `65bad44978d7b2a4f3509eb21ef48c760bf3ab9b`. Run `40004314075`: qualification job `120588205873` SUCCESS, `224 passed, 1 skipped`, locked dependency installation and `pip check` PASS; real clean-room E2E job `120589521499` SUCCESS. Runner output explicitly shows `FACTORY_VOICE_BACKEND=m6-ryan`, `Backend: m6-ryan`, Ryan WAV, WhisperX alignment file, 11 real ranked visual assets, rendered MP4, QC PASS and `M6_9_PRODUCTION_PACKAGE_PASS`.
- Exact final Gate10 acceptance output: `{"gate":10,"kind":"REAL_NONPUBLISHING_CLEANROOM","sha":"65bad44978d7b2a4f3509eb21ef48c760bf3ab9b","status":"PASS","scenes":11,"qc":"PASS","media_uploaded":false,"published":false}`. `ffprobe` verified 1080x1920, 30/1 fps and audio stream. This is real source/retrieval/TTS E2E evidence, not the synthetic M6.9 fixture canary.
- AUD-P1-009 CLOSED, DIRECT_BLOCKS=[10] only. Gates 1–9 remain PASS; Gate10 now formally PASS. P0 open=0; P1 open=0. All 10 Gates PASS with no unresolved correctness/safety blocker. Historical intermediate failures remain recorded; no test/QC assertion was weakened.
- Frozen `factory-v1-storyboard` SHA `ddd55af7ed3f7bd418b078140909750d758519bb` unchanged; Ryan/Qwen identity/quality parameters preserved. No video upload/publishing, paid services, new secrets, branch protection bypass or low-level ref manipulation. This final ledger synchronization is documentation-only; it does not invalidate exact executable SHA qualification.
- Future runs must perform drift-only verification, preserving PASS unless an exact changed blob affects an acceptance criterion. The existing automation is not paused, disabled or deleted.
