# M6.0 Human selection — Qwen3-TTS

Date: 2026-09-20
Gate status: M6.0_ENGINE_SELECTED / PRODUCTION_RIGHTS_GATE_OPEN

The human reviewer listened to the Qwen3-TTS male CustomVoice samples and explicitly selected this voice-engine direction, reporting that the voice is very pleasant to listen to and has convincing intonation.

This closes the earlier engine-direction objection caused by the robotic/emotionally detached Edge result. The human reviewer subsequently explicitly selected the tested male preset Ryan.

Approved engine direction:
- Qwen3-TTS
- official Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice technical path
- English male voice only
- selected speaker: Ryan
- instruction-directed natural/conversational/restrained delivery

Configuration freeze: `config/m6/qwen3_ryan_frozen.json`.
Rights evidence: `docs/m6/qwen3_ryan_rights_gate.md`.

Remaining blocker: the official Apache-2.0 code/checkpoint evidence does not independently establish Ryan-specific voice/personality rights. Do not infer that clearance. M6.1 remains blocked until this rights gate is resolved or an explicitly commercially cleared male voice path is selected.

No production migration is authorized by this selection. Production Edge remains unchanged. No paid service, billing or publishing is authorized.
