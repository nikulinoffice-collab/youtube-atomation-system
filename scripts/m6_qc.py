"""M6.8 vendor-neutral QC and certification screening contract.

Metrics are screening signals only; passing this module never claims naturalness.
Human review remains mandatory before any M6.9 production migration.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Mapping, Sequence

QC_VERSION = "m6.qc.v1"


class QCError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class QCMetrics:
    duration_s: float
    spoken_words: int
    wpm: float
    silence_ratio: float
    clipping_ratio: float
    mean_alignment_confidence: float
    pitch_range_semitones: float
    energy_dynamic_range_db: float

    def to_dict(self) -> dict:
        return asdict(self)


def _require_finite_nonnegative(name: str, value: float) -> None:
    if value < 0 or value != value or value in (float("inf"), float("-inf")):
        raise QCError("INVALID_METRIC", f"{name} must be finite and non-negative")


def screen_qc(
    *,
    audio: Mapping,
    plan: Mapping,
    alignment: Mapping,
    analysis: Mapping,
) -> dict:
    """Fail closed on structural/audio/timing anomalies and emit review evidence.

    `analysis` is produced by deterministic audio analysis upstream; this contract
    validates its bounded measurements and ties them to plan/alignment identity.
    Pitch/energy/contour metrics are explicitly screening signals, not proof of
    expressive quality or naturalness.
    """
    duration = float(audio["duration_s"])
    if duration <= 0:
        raise QCError("INVALID_DURATION", "audio duration must be positive")

    words = alignment.get("word_timings", [])
    if not words:
        raise QCError("MISSING_SPEECH", "alignment contains no speech")
    expected = int(alignment.get("coverage", {}).get("expected_words", -1))
    aligned = int(alignment.get("coverage", {}).get("aligned_words", -2))
    if expected <= 0 or aligned != expected or len(words) != expected:
        raise QCError("ALIGNMENT_COVERAGE", "alignment coverage is incomplete or inconsistent")

    plan_blocks = [str(b["block_id"]) for b in plan.get("blocks", [])]
    if not plan_blocks:
        raise QCError("EMPTY_PLAN", "VoicePlan contains no blocks")
    timing_blocks = []
    for word in words:
        bid = str(word["block_id"])
        if bid not in timing_blocks:
            timing_blocks.append(bid)
    if timing_blocks != plan_blocks:
        raise QCError("BLOCK_CONTINUITY", "alignment block order/coverage differs from VoicePlan")

    last_end = 0.0
    confidences = []
    for word in words:
        start, end = float(word["start_s"]), float(word["end_s"])
        confidence = float(word["confidence"])
        if start < last_end or end <= start or end > duration + 1e-6:
            raise QCError("TIMING_ANOMALY", "word timing is overlapping, reordered or outside audio")
        if not 0.0 <= confidence <= 1.0:
            raise QCError("INVALID_ALIGNMENT_CONFIDENCE", "alignment confidence outside [0,1]")
        last_end = end
        confidences.append(confidence)

    silence_ratio = float(analysis["silence_ratio"])
    clipping_ratio = float(analysis["clipping_ratio"])
    pitch_range = float(analysis["pitch_range_semitones"])
    energy_range = float(analysis["energy_dynamic_range_db"])
    for name, value in (
        ("silence_ratio", silence_ratio), ("clipping_ratio", clipping_ratio),
        ("pitch_range_semitones", pitch_range), ("energy_dynamic_range_db", energy_range),
    ):
        _require_finite_nonnegative(name, value)
    if silence_ratio > 0.45:
        raise QCError("PATHOLOGICAL_SILENCE", "silence ratio exceeds screening ceiling")
    if clipping_ratio > 0.001:
        raise QCError("CLIPPING", "clipping ratio exceeds screening ceiling")

    spoken_words = len(words)
    wpm = spoken_words / duration * 60.0
    metrics = QCMetrics(
        duration_s=duration,
        spoken_words=spoken_words,
        wpm=wpm,
        silence_ratio=silence_ratio,
        clipping_ratio=clipping_ratio,
        mean_alignment_confidence=sum(confidences) / len(confidences),
        pitch_range_semitones=pitch_range,
        energy_dynamic_range_db=energy_range,
    )
    return {
        "version": QC_VERSION,
        "status": "HUMAN_REVIEW_REQUIRED_M6_8",
        "metrics": metrics.to_dict(),
        "screening_only": True,
        "naturalness_claimed": False,
        "production_migration_permitted": False,
        "audit": {
            "audio_sha256": str(audio["sha256"]),
            "plan_version": str(plan["version"]),
            "alignment_version": str(alignment["version"]),
            "block_ids": plan_blocks,
        },
    }
