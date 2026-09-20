#!/usr/bin/env python3
"""M6.4 vendor-neutral TTS adapter contract.

This module deliberately contains no engine/model implementation. It defines the
validated request/result boundary that Qwen3 and future engines must satisfy.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from scripts.m6_voice_plan_validator import validate_voice_plan


class TTSAdapterError(RuntimeError):
    """Machine-actionable adapter boundary failure."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class SynthesisRequest:
    voice_plan: Mapping[str, Any]
    output_path: Path
    voice_id: str


@dataclass(frozen=True)
class SynthesisResult:
    adapter_id: str
    adapter_version: str
    engine_id: str
    engine_revision: str
    model_id: str
    model_revision: str
    voice_id: str
    output_path: Path
    audio_format: str
    sample_rate_hz: int
    channels: int
    device: str
    synthesis_seconds: float
    audio_seconds: float
    real_time_factor: float
    unsupported_controls: tuple[str, ...]

    def provenance(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "engine_id": self.engine_id,
            "engine_revision": self.engine_revision,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "voice_id": self.voice_id,
            "audio_format": self.audio_format,
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "device": self.device,
            "synthesis_seconds": self.synthesis_seconds,
            "audio_seconds": self.audio_seconds,
            "real_time_factor": self.real_time_factor,
            "unsupported_controls": list(self.unsupported_controls),
        }


class TTSAdapter(ABC):
    """Engine-neutral synthesis boundary. Invalid VoicePlans never reach engines."""

    adapter_id = "abstract"
    adapter_version = "m6.4-v1"

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        try:
            validate_voice_plan(dict(request.voice_plan))
        except Exception as exc:
            details = getattr(exc, "as_dict", lambda: {"message": str(exc)})()
            raise TTSAdapterError("INVALID_VOICE_PLAN", str(details)) from exc
        if request.output_path.suffix.lower() != ".wav":
            raise TTSAdapterError("LOSSLESS_WAV_REQUIRED", "M6.4 synthesis output must be .wav")
        if not request.voice_id.strip():
            raise TTSAdapterError("VOICE_ID_REQUIRED", "voice_id must be non-empty")
        result = self._synthesize_validated(request)
        self._validate_result(request, result)
        return result

    @abstractmethod
    def _synthesize_validated(self, request: SynthesisRequest) -> SynthesisResult:
        raise NotImplementedError

    def _validate_result(self, request: SynthesisRequest, result: SynthesisResult) -> None:
        if result.adapter_id != self.adapter_id or result.adapter_version != self.adapter_version:
            raise TTSAdapterError("ADAPTER_PROVENANCE_MISMATCH", "result adapter provenance does not match adapter")
        if result.voice_id != request.voice_id:
            raise TTSAdapterError("VOICE_PROVENANCE_MISMATCH", "result voice_id differs from request")
        if result.output_path != request.output_path:
            raise TTSAdapterError("OUTPUT_PATH_MISMATCH", "result output path differs from request")
        if result.audio_format != "wav" or result.sample_rate_hz <= 0 or result.channels <= 0:
            raise TTSAdapterError("INVALID_AUDIO_METADATA", "lossless WAV metadata is required")
        if not all((result.engine_id, result.engine_revision, result.model_id, result.model_revision, result.device)):
            raise TTSAdapterError("INCOMPLETE_PROVENANCE", "engine/model/device provenance must be explicit")
        if result.synthesis_seconds < 0 or result.audio_seconds <= 0 or result.real_time_factor < 0:
            raise TTSAdapterError("INVALID_RUNTIME_METRICS", "runtime metrics must be non-negative and audio duration positive")
