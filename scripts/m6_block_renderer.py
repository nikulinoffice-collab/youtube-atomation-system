#!/usr/bin/env python3
"""M6.5 deterministic semantic-block rendering and lossless WAV assembly."""
from __future__ import annotations

import hashlib
import json
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


class BlockRenderError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class WavFormat:
    sample_rate_hz: int
    channels: int
    sample_width_bytes: int


def stable_block_id(plan: dict[str, Any], block: dict[str, Any]) -> str:
    material = json.dumps({
        "plan_schema_version": plan.get("schema_version"),
        "spoken_text": plan.get("spoken_text"),
        "block": block,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "m6b-" + hashlib.sha256(material).hexdigest()[:20]


def _wav_payload(path: Path) -> tuple[WavFormat, bytes]:
    try:
        with wave.open(str(path), "rb") as wav:
            if wav.getcomptype() != "NONE":
                raise BlockRenderError("COMPRESSED_WAV_FORBIDDEN", f"{path} is not PCM WAV")
            fmt = WavFormat(wav.getframerate(), wav.getnchannels(), wav.getsampwidth())
            return fmt, wav.readframes(wav.getnframes())
    except (wave.Error, EOFError) as exc:
        raise BlockRenderError("INVALID_WAV", f"invalid WAV {path}: {exc}") from exc


def render_voice_plan_blocks(
    plan: dict[str, Any],
    output_dir: Path,
    render_block: Callable[[dict[str, Any], Path], dict[str, Any]],
    *,
    voice_id: str,
    model_id: str,
    model_revision: str,
) -> dict[str, Any]:
    """Render every VoicePlan block exactly once and return an auditable manifest."""
    blocks = plan.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise BlockRenderError("BLOCKS_REQUIRED", "VoicePlan must contain blocks")
    output_dir.mkdir(parents=True, exist_ok=True)
    expected_start = 0
    seen_ids: set[str] = set()
    records: list[dict[str, Any]] = []
    canonical_format: WavFormat | None = None

    for index, block in enumerate(blocks):
        span = block.get("spoken_span") or {}
        start, end = span.get("start"), span.get("end")
        if start != expected_start or not isinstance(end, int) or end <= start:
            raise BlockRenderError("BLOCK_ORDER_OR_COVERAGE", f"block {index} is missing, duplicated or reordered")
        block_id = stable_block_id(plan, block)
        if block_id in seen_ids:
            raise BlockRenderError("DUPLICATE_BLOCK", block_id)
        seen_ids.add(block_id)
        out = output_dir / f"{index:03d}-{block_id}.wav"
        meta = render_block(block, out)
        for key, expected in (("voice_id", voice_id), ("model_id", model_id), ("model_revision", model_revision)):
            if meta.get(key) != expected:
                raise BlockRenderError("RENDER_IDENTITY_DRIFT", f"block {index} {key} drift")
        if not out.is_file():
            raise BlockRenderError("MISSING_BLOCK_AUDIO", str(out))
        fmt, payload = _wav_payload(out)
        if canonical_format is None:
            canonical_format = fmt
        elif fmt != canonical_format:
            raise BlockRenderError("WAV_FORMAT_DRIFT", f"block {index} format differs from first block")
        records.append({
            "index": index, "block_id": block_id, "role": block.get("role"),
            "spoken_span": {"start": start, "end": end}, "wav": out.name,
            "wav_sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "pcm_bytes": len(payload),
            "voice_id": voice_id, "model_id": model_id, "model_revision": model_revision,
        })
        expected_start = end

    if expected_start != len(plan.get("spoken_text", "")):
        raise BlockRenderError("BLOCK_ORDER_OR_COVERAGE", "blocks do not cover complete spoken_text")
    assert canonical_format is not None
    return {
        "schema_version": 1, "voice_plan_schema_version": plan.get("schema_version"),
        "voice_id": voice_id, "model_id": model_id, "model_revision": model_revision,
        "wav_format": canonical_format.__dict__, "blocks": records,
    }


def assemble_lossless_wav(manifest: dict[str, Any], block_dir: Path, output_path: Path) -> dict[str, Any]:
    """Concatenate PCM frames without transcoding; fail closed on identity/format drift."""
    blocks = manifest.get("blocks") or []
    if not blocks:
        raise BlockRenderError("BLOCKS_REQUIRED", "manifest contains no blocks")
    indices = [r.get("index") for r in blocks]
    if indices != list(range(len(blocks))):
        raise BlockRenderError("MANIFEST_ORDER_INVALID", "block indices must be contiguous and ordered")
    ids = [r.get("block_id") for r in blocks]
    if len(set(ids)) != len(ids):
        raise BlockRenderError("DUPLICATE_BLOCK", "manifest contains duplicate block ids")

    expected_fmt = WavFormat(**manifest["wav_format"])
    frames: list[bytes] = []
    for record in blocks:
        path = block_dir / record["wav"]
        if not path.is_file():
            raise BlockRenderError("MISSING_BLOCK_AUDIO", str(path))
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["wav_sha256"]:
            raise BlockRenderError("BLOCK_HASH_MISMATCH", record["block_id"])
        fmt, payload = _wav_payload(path)
        if fmt != expected_fmt:
            raise BlockRenderError("WAV_FORMAT_DRIFT", record["block_id"])
        frames.append(payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(expected_fmt.channels)
        wav.setsampwidth(expected_fmt.sample_width_bytes)
        wav.setframerate(expected_fmt.sample_rate_hz)
        for payload in frames:
            wav.writeframesraw(payload)
    return {
        "output": str(output_path), "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "block_count": len(blocks), "pcm_bytes": sum(len(x) for x in frames),
        "wav_format": expected_fmt.__dict__, "assembly": "lossless_pcm_concatenation",
    }
