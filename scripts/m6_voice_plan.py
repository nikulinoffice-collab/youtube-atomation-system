#!/usr/bin/env python3
"""M6.2 deterministic, vendor-neutral VoicePlan generator."""
from __future__ import annotations

import re
from typing import Iterable

ROLES = {
    "HOOK", "QUESTION", "CONTRAST", "IMPORTANT_FACT", "REVEAL",
    "EXPLANATION", "TRANSITION", "CONCLUSION",
}

PROFILES = {
    "HOOK": (185, 1.06, 0, 180, "engage", "confident", .65, "rise-fall", 2.5, "reveal-arc"),
    "QUESTION": (165, .98, 120, 260, "ask", "curious", .52, "rise", 2.0, "question-rise"),
    "CONTRAST": (160, .96, 160, 240, "contrast", "serious", .50, "rise-fall", 1.8, "contrastive"),
    "IMPORTANT_FACT": (155, .94, 140, 260, "inform", "serious", .48, "fall", 1.5, "declarative-fall"),
    "REVEAL": (170, 1.00, 180, 320, "reveal", "confident", .60, "rise-fall", 2.2, "reveal-arc"),
    "EXPLANATION": (150, .92, 120, 220, "explain", "neutral", .42, "level", 1.0, "neutral"),
    "TRANSITION": (155, .95, 140, 180, "bridge", "neutral", .40, "level", .8, "neutral"),
    "CONCLUSION": (150, .92, 180, 360, "close", "warm", .45, "fall", 1.4, "declarative-fall"),
}


def _segments(text: str) -> list[tuple[int, int]]:
    """Return contiguous non-empty paragraph/sentence spans without losing whitespace."""
    if not text:
        return []
    ends = [m.end() for m in re.finditer(r"(?:[.!?](?=\s|$)|\n\s*\n)", text)]
    spans, start = [], 0
    for end in ends:
        if end > start:
            spans.append((start, end))
            start = end
    if start < len(text):
        spans.append((start, len(text)))
    return spans or [(0, len(text))]


def _spoken_to_display(normalized: dict, pos: int, *, end: bool = False) -> int:
    """Map a spoken boundary back to the canonical display boundary deterministically."""
    dtext, stext = normalized["display_text"], normalized["spoken_text"]
    mappings = normalized.get("mappings", [])
    dcur = scur = 0
    for m in mappings:
        unchanged = m["spoken_start"] - scur
        if pos <= scur + unchanged:
            return min(len(dtext), dcur + (pos - scur))
        dcur += unchanged
        scur += unchanged
        if pos <= m["spoken_end"]:
            return m["display_end"] if end or pos == m["spoken_end"] else m["display_start"]
        dcur = m["display_end"]
        scur = m["spoken_end"]
    return min(len(dtext), dcur + (pos - scur))


def _role_for(text: str, index: int, count: int, metadata: dict | None) -> str:
    if metadata and index < len(metadata.get("roles", [])):
        role = metadata["roles"][index]
        if role not in ROLES:
            raise ValueError(f"unsupported VoicePlan role: {role}")
        return role
    stripped = text.strip()
    low = stripped.lower()
    if stripped.endswith("?"):
        return "QUESTION"
    if re.search(r"\b(but|however|instead|unlike|while)\b", low):
        return "CONTRAST"
    if re.search(r"\b(the key|the result|reveals?|turns out)\b", low):
        return "REVEAL"
    if re.search(r"\b([0-9]+|percent|million|billion)\b", low):
        return "IMPORTANT_FACT"
    if index == 0:
        return "HOOK"
    if index == count - 1:
        return "CONCLUSION"
    if re.match(r"\s*(next|now|meanwhile|so)\b", low):
        return "TRANSITION"
    return "EXPLANATION"


def _pronunciation_refs(normalized: dict, s0: int, s1: int) -> list[str]:
    refs = []
    for m in normalized.get("mappings", []):
        if m.get("rule") == "lexicon" and m["spoken_start"] < s1 and m["spoken_end"] > s0:
            refs.append(m["display"])
    return sorted(set(refs))


def generate_voice_plan(normalized: dict, semantic_metadata: dict | None = None) -> dict:
    spoken = normalized["spoken_text"]
    spans = _segments(spoken)
    if not spans:
        raise ValueError("cannot build VoicePlan for empty spoken_text")
    blocks = []
    for i, (s0, s1) in enumerate(spans):
        role = _role_for(spoken[s0:s1], i, len(spans), semantic_metadata)
        wpm, rate, pre, post, intent, emotion, energy, pitch, pitch_range, contour = PROFILES[role]
        blocks.append({
            "block_id": f"vp1-b{i+1:04d}",
            "role": role,
            "display_span": {"start": _spoken_to_display(normalized, s0), "end": _spoken_to_display(normalized, s1, end=True)},
            "spoken_span": {"start": s0, "end": s1},
            "target_wpm": wpm, "rate": rate,
            "pre_pause_ms": pre, "post_pause_ms": post,
            "internal_pauses": [], "intent": intent, "emotion": emotion,
            "energy": energy, "pitch_direction": pitch,
            "pitch_range_semitones": pitch_range, "intonation_contour": contour,
            "emphasis": [], "pronunciation_refs": _pronunciation_refs(normalized, s0, s1),
        })
    return {
        "schema_version": 1, "voice_plan_version": "m6.2-v1",
        "normalizer_version": normalized["normalizer_version"],
        "lexicon_version": normalized["lexicon_version"],
        "lexicon_sha256": normalized["lexicon_sha256"],
        "display_text": normalized["display_text"], "spoken_text": spoken,
        "blocks": blocks,
    }
