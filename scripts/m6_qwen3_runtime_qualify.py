#!/usr/bin/env python3
"""M6.4 special real-runtime qualification for pinned Qwen3/Ryan.

This script is intentionally outside normal unit qualification. It loads the
pinned model revision, performs one short non-paid synthesis, writes lossless
WAV, and emits bound runtime/provenance metrics. It never publishes audio.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import subprocess
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/m6/qwen3_ryan_frozen.json"
OUT = Path(os.environ.get("M6_RUNTIME_OUT", ROOT / "artifacts/m6_4_runtime"))
TEXT = "This is a short internal voice qualification."


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> int:
    cfg = json.loads(CONFIG_PATH.read_text())
    if cfg.get("speaker") != "Ryan" or cfg.get("production_enabled") is not False or cfg.get("paid_services") is not False:
        raise SystemExit("frozen config violates Ryan development-only / zero-cost invariant")

    try:
        import torch
        from qwen_tts import Qwen3TTSModel
    except Exception as exc:
        raise SystemExit(f"QWEN_RUNTIME_IMPORT_FAILED: {exc}") from exc

    if not hasattr(Qwen3TTSModel, "from_pretrained"):
        raise SystemExit("QWEN_RUNTIME_API_INCOMPATIBLE: Qwen3TTSModel.from_pretrained missing")

    OUT.mkdir(parents=True, exist_ok=True)
    wav_path = OUT / "m6_4_ryan_runtime.wav"
    metrics_path = OUT / "m6_4_ryan_runtime_metrics.json"

    device = "cpu"
    dtype = torch.float32
    load_started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(
        cfg["model"],
        revision=cfg["model_revision"],
        device_map=device,
        dtype=dtype,
    )
    load_seconds = time.perf_counter() - load_started

    started = time.perf_counter()
    wavs, sr = model.generate_custom_voice(
        text=TEXT,
        language=cfg["language"],
        speaker=cfg["speaker"],
        instruct=cfg["instruction"],
        **cfg["generation"],
    )
    synthesis_seconds = time.perf_counter() - started
    if not wavs:
        raise SystemExit("QWEN_RUNTIME_EMPTY_AUDIO")

    audio = wavs[0]
    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    try:
        import numpy as np
        pcm = np.clip(np.asarray(audio, dtype=np.float32), -1.0, 1.0)
        pcm16 = (pcm * 32767.0).astype("<i2")
    except Exception as exc:
        raise SystemExit(f"QWEN_RUNTIME_AUDIO_CONVERSION_FAILED: {exc}") from exc

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr))
        wf.writeframes(pcm16.tobytes())

    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
    if frames <= 0 or sample_rate <= 0 or channels != 1 or sample_width != 2:
        raise SystemExit("QWEN_RUNTIME_INVALID_WAV")
    audio_seconds = frames / sample_rate
    if audio_seconds <= 0:
        raise SystemExit("QWEN_RUNTIME_INVALID_DURATION")

    peak_ram_kib = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    metrics = {
        "schema_version": 1,
        "milestone": "M6.4",
        "qualification": "real_qwen3_ryan_synthesis",
        "git_sha": _git_head(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "engine_source_repository": cfg["source_repository"],
        "engine_source_commit": cfg["source_commit"],
        "package_version": cfg["package_version"],
        "model": cfg["model"],
        "model_revision": cfg["model_revision"],
        "language": cfg["language"],
        "speaker": cfg["speaker"],
        "device": device,
        "dtype": "float32",
        "load_seconds": load_seconds,
        "synthesis_seconds": synthesis_seconds,
        "audio_seconds": audio_seconds,
        "real_time_factor": synthesis_seconds / audio_seconds,
        "peak_ram_kib": peak_ram_kib,
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "wav_sha256": _sha256(wav_path),
        "wav_bytes": wav_path.stat().st_size,
        "production_enabled": False,
        "paid_services": False,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
