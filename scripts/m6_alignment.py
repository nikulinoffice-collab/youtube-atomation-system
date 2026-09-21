"""M6.7 vendor-neutral canonical timing/alignment contract.

This module deliberately separates canonical text/span identity from any concrete
forced-aligner.  An aligner may emit observations, but only observations that
round-trip to the VoicePlan's exact spoken/display spans can become timing data.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable, Mapping, Sequence

ALIGNMENT_VERSION = "m6.alignment.v1"


class AlignmentError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class WordTiming:
    block_id: str
    spoken_span_id: str
    display_span_id: str
    token_index: int
    spoken_text: str
    display_text: str
    start_s: float
    end_s: float
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


def _words(text: str) -> list[str]:
    return text.split()


def validate_timings(timings: Sequence[WordTiming], *, duration_s: float | None = None) -> None:
    if not timings:
        raise AlignmentError("EMPTY_ALIGNMENT", "alignment contains no word timings")
    previous_end = 0.0
    seen: set[tuple[str, str, int]] = set()
    for item in timings:
        if item.start_s < 0 or item.end_s <= item.start_s:
            raise AlignmentError("INVALID_TIME_RANGE", f"invalid timing for {item.spoken_span_id}:{item.token_index}")
        if not 0.0 <= item.confidence <= 1.0:
            raise AlignmentError("INVALID_CONFIDENCE", f"confidence outside [0,1] for {item.spoken_span_id}:{item.token_index}")
        if item.start_s < previous_end:
            raise AlignmentError("NON_MONOTONIC_OR_OVERLAP", f"overlap/reorder at {item.spoken_span_id}:{item.token_index}")
        key = (item.block_id, item.spoken_span_id, item.token_index)
        if key in seen:
            raise AlignmentError("DUPLICATE_WORD", f"duplicate timing {key}")
        seen.add(key)
        previous_end = item.end_s
    if duration_s is not None and previous_end > duration_s + 1e-6:
        raise AlignmentError("PAST_AUDIO_END", "alignment extends beyond audio duration")


def canonicalize_observations(
    blocks: Sequence[Mapping],
    observations: Iterable[Mapping],
    *,
    duration_s: float | None = None,
) -> dict:
    """Bind aligner observations to canonical VoicePlan spans, fail-closed.

    Each block must carry block_id plus spoken/display span objects with id/text.
    Observations are intentionally vendor-neutral and must identify block_id,
    spoken_span_id, token_index, start_s/end_s/confidence.  Canonical text always
    comes from the plan, so display forms such as "$2.4B" survive even when the
    spoken form is expanded.
    """
    canonical: dict[tuple[str, str], tuple[str, str, str]] = {}
    expected: list[tuple[str, str, int]] = []
    for block in blocks:
        bid = str(block["block_id"])
        spoken = block["spoken_span"]
        display = block["display_span"]
        sid, did = str(spoken["id"]), str(display["id"])
        spoken_text, display_text = str(spoken["text"]), str(display["text"])
        canonical[(bid, sid)] = (did, spoken_text, display_text)
        expected.extend((bid, sid, i) for i, _ in enumerate(_words(spoken_text)))

    by_key: dict[tuple[str, str, int], Mapping] = {}
    for obs in observations:
        key = (str(obs["block_id"]), str(obs["spoken_span_id"]), int(obs["token_index"]))
        if key not in expected:
            raise AlignmentError("UNKNOWN_MAPPING", f"observation does not map to canonical token {key}")
        if key in by_key:
            raise AlignmentError("DUPLICATE_WORD", f"duplicate observation {key}")
        by_key[key] = obs

    if set(by_key) != set(expected):
        missing = [key for key in expected if key not in by_key]
        raise AlignmentError("MISSING_COVERAGE", f"missing canonical tokens: {missing}")

    timings: list[WordTiming] = []
    for bid, sid, index in expected:
        obs = by_key[(bid, sid, index)]
        did, spoken_text, display_text = canonical[(bid, sid)]
        spoken_words = _words(spoken_text)
        display_words = _words(display_text)
        timings.append(WordTiming(
            block_id=bid,
            spoken_span_id=sid,
            display_span_id=did,
            token_index=index,
            spoken_text=spoken_words[index],
            display_text=display_words[index] if len(display_words) == len(spoken_words) else display_text,
            start_s=float(obs["start_s"]),
            end_s=float(obs["end_s"]),
            confidence=float(obs["confidence"]),
        ))

    validate_timings(timings, duration_s=duration_s)
    return {
        "version": ALIGNMENT_VERSION,
        "word_timings": [item.to_dict() for item in timings],
        "coverage": {"expected_words": len(expected), "aligned_words": len(timings)},
    }
