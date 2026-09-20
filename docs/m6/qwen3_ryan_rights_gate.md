# Qwen3-TTS / Ryan rights gate

Date: 2026-09-20
Selected path: Qwen3-TTS 12Hz 0.6B CustomVoice / English / Ryan.
Gate decision: CLOSED_FOR_DEVELOPMENT / FAIL_CLOSED_FOR_PUBLISHING.

## Official-source audit

1. Code/repository — PASS.
   The official QwenLM/Qwen3-TTS repository is distributed under Apache License 2.0 (Copyright 2026 Alibaba Cloud).

2. Exact model/checkpoint — PASS.
   The official Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice checkpoint used by the project is marked Apache-2.0. Frozen model revision: 85e237c12c027371202489a0ec509ded67b5e4b5.

3. Ryan built-in speaker — DEVELOPMENT PASS / PRODUCTION CLEARANCE NOT PROVEN.
   Ryan is an official built-in English CustomVoice speaker and is therefore valid for the selected technical path. The reviewed official Qwen/Alibaba repository, model card and license materials do not provide a separate Ryan-specific provenance, publicity/personality-rights statement, or an explicit Ryan-specific commercial-use grant.

4. Generated-output/commercial-use restriction — NO MODEL-SPECIFIC PROHIBITION FOUND / RYAN-SPECIFIC CLEARANCE NOT PROVEN.
   Apache-2.0 provides broad rights for the licensed Work. No additional commercial-output prohibition was found in the reviewed official model materials. This is not treated as affirmative evidence that every possible third-party voice/personality right associated with the Ryan preset is cleared.

## Engineering decision

The rights investigation is considered complete for the current development milestone; absence of Ryan-specific authoritative evidence will not block M6.1–M6.8 engineering work.

Ryan is APPROVED for:
- local/CI technical development;
- automated synthesis tests;
- benchmark and QC work;
- internal human listening/review;
- building the vendor-neutral M6 pipeline.

Ryan is NOT YET APPROVED for:
- public production publishing;
- monetized YouTube/TikTok output;
- any external distribution where commercial/personality-rights clearance is required.

Publishing remains fail-closed. Before M6.9 production migration, one of these conditions must be satisfied:
A. authoritative Ryan-specific commercial/personality-rights evidence is obtained; or
B. the production speaker is replaced by a Factory-owned or explicitly commercially licensed male voice/reference path and passes the M6.8 quality gate.

## Evidence boundary

Official repository: https://github.com/QwenLM/Qwen3-TTS
Repository license: Apache-2.0.
Official checkpoint: Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice.
Checkpoint license: Apache-2.0.
Frozen project config: config/m6/qwen3_ryan_frozen.json.

This is a conservative engineering rights classification, not legal advice.

Production Edge remains unchanged. No paid service, billing, secrets or publishing are authorized by this gate.
