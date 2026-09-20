# Qwen3-TTS / Ryan rights gate

Date: 2026-09-20
Selected path: Qwen3-TTS 12Hz 0.6B CustomVoice / English / Ryan.

## Four-part gate

1. Code/repository: PASS. Official QwenLM/Qwen3-TTS repository is Apache-2.0.
2. Model/checkpoint: PASS. The exact official 0.6B CustomVoice checkpoint revision used for qualification is published as Apache-2.0.
3. Built-in Ryan voice/personality asset: UNRESOLVED. Official Qwen documentation explicitly lists Ryan as a supported built-in English speaker ("Dynamic male voice with strong rhythmic drive"), so its inclusion in the official model is established. However, the reviewed official materials do not contain a separate Ryan-specific provenance/personality/voice-rights statement.
4. Commercial generated-output restrictions attributable to Ryan: UNRESOLVED. Apache-2.0 grants broad rights in the licensed Work and the checkpoint is marked Apache-2.0; no additional model-card restriction on commercial output was found. This evidence still does not independently prove third-party personality/voice rights for the Ryan preset.

## Evidence boundary

Official repository: https://github.com/QwenLM/Qwen3-TTS
Official repository license: Apache-2.0.
Official checkpoint: Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice, Apache-2.0.
Official documentation lists Ryan as a supported built-in English speaker.

The audit found no authoritative Ryan-specific rights statement beyond inclusion in the Apache-2.0-distributed model. Absence of an additional restriction is not treated as affirmative personality-rights clearance.

## Disposition

ENGINE_QUALITY_SELECTED / RYAN_RIGHTS_EVIDENCE_INCOMPLETE / FAIL_CLOSED_FOR_PUBLISHING.

Ryan is frozen for technical development because it is the human-selected quality target. Publishing with Ryan is not automatically enabled. The project must obtain authoritative Ryan-specific clearance, or replace the production speaker path with a Factory-owned/explicitly commercially licensed male reference voice while preserving Qwen3-TTS as the selected engine.

This is a conservative engineering rights gate, not legal advice.

Production Edge remains unchanged. No paid service, billing, secrets or publishing are authorized by this document.
