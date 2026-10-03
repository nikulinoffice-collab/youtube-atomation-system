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
| AUD-P1-002 | P1 | Script topic history reads/writes `agents/output/recent_topics.json` while tracked canonical history is `agents/state/recent_topics.json`. | OPEN |
| AUD-P1-003 | P1 | Cross-run anti-repeat state is not persisted by the read-only draft workflow. | OPEN; design/fail-closed resolution required |
| AUD-P1-004 | P1 | `upload_agent.py` is an independently executable publishing entry point without an explicit opt-in authorization gate and defaults to public visibility. | OPEN |
| AUD-P1-008 | P1 | Edge rollback path in `voice_agent.py` contains a literal `\\n` after the lazy `import edge_tts`, commenting out the `communicate = edge_tts.Communicate(...)` assignment; rollback execution reaches `communicate.stream()` with `communicate` undefined. Existing route/media tests assert rollback selection/artifact resolution but do not execute rollback synthesis. | OPEN; restore executable assignment and add rollback-path regression test |
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
