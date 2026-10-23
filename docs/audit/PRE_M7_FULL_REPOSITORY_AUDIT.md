# PRE-M7 Full Repository Audit

Status: IN_PROGRESS

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
5. Data flow/contracts — IN_PROGRESS
6. GitHub Actions/automation — IN_PROGRESS
7. Tests/QC/fail-closed — IN_PROGRESS
8. Security/cost/publishing — PASS
9. Controlled cleanup/refactor — NOT_STARTED
10. Clean-room E2E qualification — NOT_STARTED

## Findings ledger
| ID | Severity | Finding | Status |
|---|---|---|---|
| AUD-P1-001 | P1 | Draft/full-production dependency environment previously lacked exact shared enforcement for the validated Ryan runtime and the complete production graph. DIRECT_BLOCKS=[4,6,7,10]. | CLOSED — shared 189-package exact constraints lock is enforced by qualification and draft workflows; `qwen-tts==0.1.1` and `whisperx==3.8.6` remain frozen; dependency-contract regression executed in exact-SHA M6 Qualification `38703875490`, job `116318345733`, on `0fdea313c8446d2112859d4fd5420e6e3b31ffcd`: SUCCESS, 128 passed / 1 skipped, `pip check` PASS. |
| AUD-P1-002 | P1 | Script topic history previously used `agents/output/recent_topics.json`; production code now uses canonical `agents/state/recent_topics.json` with state-directory creation and contract tests. DIRECT_BLOCKS=[5,7,10]. | CLOSED — implementation `22626f8b` and tests `36357bd5` are contained in exact-SHA-qualified `a65f7c69598f68868dce12f1efafb4079d2b53cb`; M6 Qualification run `37205491751`, job `111445703429` SUCCESS and executed the state-contract test suite. |
| AUD-P1-003 | P1 | Cross-run anti-repeat history was not persisted across read-only draft runs. DIRECT_BLOCKS=[5,6,7,10]. | CLOSED — cache restore/save and explicit fail-closed cache-miss bootstrap in `.github/workflows/publish.yml@09ee25fae9f895484d295abd084d4b6c0c29628d`; malformed restored-state rejection in `agents/script_agent.py@ff9bdaf2632776ac580fb1b7e04e06098bc778ee`; restored/empty/corrupt/continuity regressions in `tests/test_pre_m7_state_contracts.py@6e52e96b5e4a9375e5d57fc0339669256d5b4d33`. Exact executable SHA `7e898c57108966d0e4c81e07a218d1a681104a88`, M6 Qualification run `39925089835`, job `120319389641` SUCCESS (140 passed / 1 skipped); no contents:write or publishing. Cache eviction/miss fails closed unless explicitly bootstrapped. |
| AUD-P1-004 | P1 | `upload_agent.py` independently executable publishing entry point remediated with default-private plus explicit `YOUTUBE_PUBLISH_AUTHORIZED=true` as the first `main()` operation before artifact discovery/OAuth/API/network. DIRECT_BLOCKS=[8,10]. | CLOSED — corrected implementation `94b0f477b54b9f0655c8b627f66335eb7fa9b6f4` contained in exact-SHA-qualified `a65f7c69598f68868dce12f1efafb4079d2b53cb`; M6 Qualification run `37205491751`, job `111445703429` SUCCESS. |
| AUD-P1-008 | P1 | Edge rollback executable defect was corrected and a direct no-network rollback synthesis regression was added. DIRECT_BLOCKS=[6,7,10]. | CLOSED — exact-SHA qualification succeeded for `140a5d4c454fa06b0bfa553d779e85f641893344` in M6 Qualification run `37103103913`; fix remains contained in latest qualified executable `0fdea313c8446d2112859d4fd5420e6e3b31ffcd`. |
| AUD-P2-001 | P2 | README and some module documentation still describe legacy Edge/automatic publishing behavior inconsistent with the current manual draft-only Ryan route. | OPEN |
| AUD-P2-002 | P2 | M5 storyboard/retrieval/ranking guarantees rely heavily on workflow inline assertions rather than a dedicated regression test layer. | OPEN |
| AUD-P3-001 | P3 | Temporary M6.9 canary workflow remains after M6.9 closure. | REVIEW after audit evidence no longer depends on it |

## Confirmed safety state
- Production route remains committed-route driven.
- Publishing is disabled in the M6.9 route.
- Pre-M7 audit does not invoke `upload_agent.py` or any social/video upload action.
- Frozen storyboard branch has not been modified.
- Frozen Ryan/Qwen identity/quality parameters have not been modified.

## Current checkpoint
- Latest exact-SHA-qualified executable/config revision: `7e898c57108966d0e4c81e07a218d1a681104a88`.
- M6 Qualification run `39925089835`, job `120319389641`: SUCCESS; `140 passed, 1 skipped`; locked production install and `pip check` PASS.
- Formal Gates PASS: 1, 2, 3, 4, 8 = 5/10.
- P0 open: 0.
- AUD-P1-001, AUD-P1-002, AUD-P1-003, AUD-P1-004 and AUD-P1-008 are CLOSED.
- Next direct blockers: qualification watch/enforcement regression for Gate 6, then visual-contract and provenance/data-contract for Gates 5/7/10.
- Gate 9 remains blocked until Gates 1–8 PASS; Gate 10 remains blocked until its direct prerequisites are closed.

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
