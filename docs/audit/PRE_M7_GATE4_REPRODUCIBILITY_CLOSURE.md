# PRE-M7 Gate 4 reproducibility closure evidence

Status: PASS

## Qualified state
- Exact executable/config SHA: `0fdea313c8446d2112859d4fd5420e6e3b31ffcd`.
- M6 Qualification run: `38703875490`.
- Qualification job: `116318345733`.
- Result: SUCCESS — `128 passed, 1 skipped`; `pip check` PASS.
- Python runtime: exact `3.11.17`.
- Qualification runner family: `ubuntu-24.04`; observed image `20261012.334.1`.
- Frozen `factory-v1-storyboard`: `ddd55af7ed3f7bd418b078140909750d758519bb`; unchanged.

## Canonical production dependency lock
`constraints/m6-qualification.txt` is the shared production constraints lock (blob `b18072acbb3fbb7d282b6bf4516a112c8a1dfe65`).

The lock contains 189 exact-pinned packages derived from a known-good exact-SHA qualification environment, including all direct production requirements and their resolved transitive graph. Frozen voice runtime identities remain exactly:
- `qwen-tts==0.1.1`
- `whisperx==3.8.6`

The full freeze source was exact-SHA-qualified `acead363a620254ce5f086e956ca5d9be3c519c6`, M6 Qualification run `38702825288`, job `116314895054`, SUCCESS with `128 passed, 1 skipped` and `pip check` PASS.

## Workflow enforcement
- `.github/workflows/m6-qualification.yml` blob `856c68ff07bb21fa3a1b7363aa0788c91de07235` watches `constraints/**`, installs `requirements.txt` through the shared constraints lock, runs `pip check`, records the resolved environment, and executes the dependency-contract regression.
- `.github/workflows/publish.yml` blob `32a9a402f0c740c781820e44d3811a2d02bed70b` uses the same constraints lock and `pip check`, pins Python `3.11.17`, uses `ubuntu-24.04`, records ffmpeg and Python/package identity, and installs the Playwright browser from exact-pinned `playwright==1.64.0`.
- `tests/test_pre_m7_dependency_contracts.py` blob `715c33746ba2e393dca679b9db4bf398b60b8f80` fails if any direct production requirement is absent from constraints, if a direct dependency is not exact-pinned, if either workflow bypasses the shared constraints lock, or if frozen Qwen/WhisperX/Python runtime identities drift.

## External-interface boundaries
- GitHub-hosted runner image patch revisions and Ubuntu apt repository contents remain provider-managed external boundaries. The runner family is pinned to `ubuntu-24.04`; the exact image revision is recorded in qualification logs.
- ffmpeg is obtained from the Ubuntu 24.04 package repository. The draft workflow records `ffmpeg -version`; renderer/QC gates fail closed on incompatible behavior.
- Playwright Python is exact-pinned and its Chromium installation is coupled to that package version; OS browser dependencies installed by Playwright remain Ubuntu-managed.
- Existing Gemini/Pexels interfaces continue to require their pre-existing secrets before draft generation. No new secret, paid service, billing action, publishing call, or upload call was introduced by Gate 4 closure.
- YouTube publishing remains isolated behind the already-closed explicit authorization/default-deny uploader boundary and is not invoked by qualification.

These residual provider-managed image/apt boundaries are observable at runtime and guarded by exact-SHA install validation, `pip check`, regression tests, renderer/QC checks, and explicit no-publishing constraints. They are not unresolved correctness, safety, or cost blockers for Gate 4.

## Gate decision
Gate 4 — Dependencies/external interfaces: PASS.

AUD-P1-001 is closure-ready from this exact evidence: full production dependencies are installed during qualification, the frozen Ryan runtime packages are present and exact-pinned, the draft workflow consumes the same lock, focused dependency-contract regression is executed, and the final exact SHA is green.
