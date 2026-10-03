# PRE-M7 Full Repository Audit

Status: IN_PROGRESS

## Baseline
- Active branch: `factory-v1-voice-m6`
- Starting audited HEAD: `a5ba707fe7ca96d3ce4ef6ba5ab1b3ba18d72e70`
- Frozen branch: `factory-v1-storyboard`
- Frozen SHA verified: `ddd55af7ed3f7bd418b078140909750d758519bb`
- M6.9 production behavior and frozen Ryan/Qwen identity are immutable audit constraints.

## Gate status
1. Inventory — IN_PROGRESS
2. Architecture — IN_PROGRESS
3. Line-by-line static audit — IN_PROGRESS
4. Dependencies/external interfaces — IN_PROGRESS
5. Data flow/contracts — IN_PROGRESS
6. GitHub Actions/automation — IN_PROGRESS
7. Tests/QC/fail-closed — IN_PROGRESS
8. Security/cost/publishing — IN_PROGRESS
9. Controlled cleanup/refactor — NOT_STARTED
10. Clean-room E2E qualification — NOT_STARTED

## Findings ledger
| ID | Severity | Finding | Status |
|---|---|---|---|
| AUD-P1-001 | P1 | Draft workflow installs `requirements.txt`, but the validated Ryan runtime dependencies `qwen-tts==0.1.1` and `whisperx==3.8.6` were absent. | FIX_COMMITTED; exact-SHA qualification pending |
| AUD-P1-002 | P1 | Script topic history previously used `agents/output/recent_topics.json`; production code now uses canonical `agents/state/recent_topics.json` with state-directory creation and contract tests. | COMMITTED (`22626f8b`, tests `36357bd5`); exact-SHA qualification pending |
| AUD-P1-003 | P1 | Cross-run anti-repeat state is not persisted by the read-only draft workflow. | OPEN; design/fail-closed resolution required |
| AUD-P1-004 | P1 | `upload_agent.py` is an independently executable publishing entry point without an explicit opt-in authorization gate and defaults to public visibility. | OPEN |
| AUD-P1-008 | P1 | Edge rollback executable defect was corrected and a direct no-network rollback synthesis regression was added. | COMMITTED (`a54d7f93` test, `140a5d4c` fix); exact-SHA qualification pending |
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
The dependency drift fix was committed first. Continue from live HEAD, qualify all executable/environment changes on their exact SHA, close P1 findings before cleanup, then complete inventory, requirement-test matrix, clean-room non-publishing E2E evidence, and final PASS criteria.

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
