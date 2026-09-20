# M6.0 Human selection — Qwen3-TTS

Date: 2026-09-20
Gate status: M6.0_ENGINE_SELECTED / DEVELOPMENT_RIGHTS_GATE_CLOSED / PUBLISHING_FAIL_CLOSED

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

Rights decision: the Ryan investigation is closed for development. Ryan may be used through M6.1–M6.8 for technical development, CI, benchmarks, QC and internal human review. Public/monetized publishing remains fail-closed until Ryan-specific authoritative clearance is obtained or a Factory-owned/explicitly commercially licensed male voice path replaces it. This unresolved publishing clearance does not block M6.1 engineering.

No production migration is authorized by this selection. Production Edge remains unchanged. No paid service, billing or publishing is authorized.
