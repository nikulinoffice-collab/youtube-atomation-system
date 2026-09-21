#!/usr/bin/env python3
"""M6.6 restrained technical mastering.

This module deliberately limits mastering to technical normalization. It preserves
an unmastered input, rejects pathological audio, records exact FFmpeg invocation,
and never treats DSP as a repair for poor synthesis.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import wave
from dataclasses import asdict, dataclass
from pathlib import Path


class MasteringError(RuntimeError):
    """Fail-closed mastering error."""


@dataclass(frozen=True)
class WavStats:
    sample_rate: int
    channels: int
    sample_width: int
    frames: int
    duration_s: float
    peak_fraction: float
    silence_fraction: float


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_pcm16_wav(path: Path, silence_threshold: int = 64) -> WavStats:
    with wave.open(str(path), "rb") as w:
        channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        if width != 2 or channels not in (1, 2) or rate <= 0 or frames <= 0:
            raise MasteringError("unsupported_or_empty_pcm_wav")
        raw = w.readframes(frames)
    samples = memoryview(raw).cast("h")
    if not samples:
        raise MasteringError("empty_pcm_payload")
    peak = max(abs(int(x)) for x in samples) / 32768.0
    silent = sum(1 for x in samples if abs(int(x)) <= silence_threshold) / len(samples)
    return WavStats(rate, channels, width, frames, frames / rate, peak, silent)


def validate_source(stats: WavStats) -> None:
    if stats.peak_fraction >= 0.9999:
        raise MasteringError("source_clipping_detected_resynthesize")
    if stats.silence_fraction > 0.80:
        raise MasteringError("pathological_silence_resynthesize")


def ffmpeg_version(ffmpeg: str = "ffmpeg") -> str:
    p = subprocess.run([ffmpeg, "-version"], check=True, capture_output=True, text=True)
    return p.stdout.splitlines()[0].strip()


def master_wav(source: Path, output: Path, manifest: Path, *, ffmpeg: str = "ffmpeg") -> dict:
    """Apply only restrained loudness/true-peak limiting and persist provenance."""
    source, output, manifest = map(Path, (source, output, manifest))
    if source.resolve() == output.resolve():
        raise MasteringError("unmastered_source_must_be_preserved")
    before = inspect_pcm16_wav(source)
    validate_source(before)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Single-pass loudnorm is intentionally technical, not expressive DSP.
    filt = "loudnorm=I=-16:LRA=11:TP=-1.5"
    cmd = [ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", str(source), "-af", filt,
           "-c:a", "pcm_s16le", "-ar", str(before.sample_rate), "-ac", str(before.channels), str(output)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    after = inspect_pcm16_wav(output)
    if after.peak_fraction >= 0.9999:
        raise MasteringError("mastered_clipping_detected")
    if abs(after.duration_s - before.duration_s) > max(0.02, 1.0 / before.sample_rate):
        raise MasteringError("mastering_changed_duration")
    record = {
        "schema_version": "m6.mastering.v1",
        "policy": "restrained_technical_only",
        "source_preserved": source.exists(),
        "source": {"path": str(source), "sha256": sha256_file(source), "stats": asdict(before)},
        "mastered": {"path": str(output), "sha256": sha256_file(output), "stats": asdict(after)},
        "ffmpeg_version": ffmpeg_version(ffmpeg),
        "ffmpeg_command": cmd,
        "filter": filt,
        "poor_tts_action": "resynthesize_not_dsp",
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
