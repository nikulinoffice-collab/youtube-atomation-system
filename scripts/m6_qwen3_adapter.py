#!/usr/bin/env python3
"""M6.4 pinned Qwen3/Ryan adapter.

The adapter is deliberately dependency-injected: importing this module never loads
Qwen or a model. Runtime loading belongs to the special qualification boundary.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from scripts.m6_tts_adapter import SynthesisRequest, SynthesisResult, TTSAdapter, TTSAdapterError

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/m6/qwen3_ryan_frozen.json"


class Qwen3RyanAdapter(TTSAdapter):
    adapter_id = "qwen3-ryan"
    adapter_version = "m6.4-v1"

    def __init__(self, engine: Callable[..., dict[str, Any]], config_path: Path = CONFIG_PATH):
        self.engine = engine
        self.config = json.loads(config_path.read_text())
        self._validate_config()

    def _validate_config(self) -> None:
        c = self.config
        required = ("source_commit", "model", "model_revision", "speaker", "language", "instruction")
        if any(not c.get(k) for k in required):
            raise TTSAdapterError("INVALID_FROZEN_CONFIG", "Qwen3/Ryan revisions and voice identity must be pinned")
        if c["speaker"] != "Ryan" or c.get("production_enabled") is not False:
            raise TTSAdapterError("RYAN_DEVELOPMENT_ONLY", "frozen Ryan config must remain development-only")
        if c.get("paid_services") is not False:
            raise TTSAdapterError("PAID_SERVICE_FORBIDDEN", "M6 adapter must remain zero-cost")

    def _instruction_for(self, plan: dict[str, Any]) -> str:
        roles = ", ".join(block["role"].lower().replace("_", " ") for block in plan["blocks"])
        return f'{self.config["instruction"]} Semantic flow: {roles}. Respect planned pauses and restrained emphasis.'

    def _synthesize_validated(self, request: SynthesisRequest) -> SynthesisResult:
        c = self.config
        if request.voice_id != c["speaker"]:
            raise TTSAdapterError("FROZEN_VOICE_MISMATCH", "M6.4 Qwen adapter is pinned to Ryan")
        unsupported = ("exact_wpm", "exact_pitch_semitones", "exact_energy")
        payload = {
            "text": request.voice_plan["spoken_text"],
            "language": c["language"],
            "speaker": c["speaker"],
            "instruction": self._instruction_for(dict(request.voice_plan)),
            "generation": dict(c["generation"]),
            "output_path": str(request.output_path),
        }
        metrics = self.engine(**payload)
        for key in ("sample_rate_hz", "channels", "device", "synthesis_seconds", "audio_seconds"):
            if key not in metrics:
                raise TTSAdapterError("ENGINE_RESULT_INCOMPLETE", f"engine result missing {key}")
        audio_seconds = float(metrics["audio_seconds"])
        synthesis_seconds = float(metrics["synthesis_seconds"])
        if audio_seconds <= 0:
            raise TTSAdapterError("ENGINE_RESULT_INVALID", "audio duration must be positive")
        return SynthesisResult(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            engine_id="QwenLM/Qwen3-TTS",
            engine_revision=c["source_commit"],
            model_id=c["model"],
            model_revision=c["model_revision"],
            voice_id=c["speaker"],
            output_path=request.output_path,
            audio_format="wav",
            sample_rate_hz=int(metrics["sample_rate_hz"]),
            channels=int(metrics["channels"]),
            device=str(metrics["device"]),
            synthesis_seconds=synthesis_seconds,
            audio_seconds=audio_seconds,
            real_time_factor=synthesis_seconds / audio_seconds,
            unsupported_controls=unsupported,
        )
