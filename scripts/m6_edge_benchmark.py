#!/usr/bin/env python3
"""M6.0 shadow benchmark runner for the existing free Edge TTS baseline.

Writes benchmark-only audio and measurements. It never imports or modifies the
production voice agent and uses no repository secrets.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import resource
import subprocess
import time
from pathlib import Path

import edge_tts

VOICE = "en-US-AriaNeural"
ENGINES = {
    "edge_legacy": {"rate": "+0%", "pitch": "+0Hz"},
    "edge_directed": {"rate": "-4%", "pitch": "+0Hz"},
}


def audio_duration(path: Path) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(p.stdout.strip())


async def synthesize(text: str, output: Path, rate: str, pitch: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    await edge_tts.Communicate(text, VOICE, rate=rate, pitch=pitch).save(str(output))


def load_cases(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("benchmark corpus must contain cases")
    return cases


def run(corpus: Path, out_dir: Path) -> dict:
    cases = load_cases(corpus)
    results = []
    started_all = time.perf_counter()
    for engine, controls in ENGINES.items():
        for case in cases:
            text = case["text"]
            sample_id = hashlib.sha256(f"{engine}:{case['id']}:{text}".encode()).hexdigest()[:12]
            audio = out_dir / "audio" / f"sample_{sample_id}.mp3"
            before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            started = time.perf_counter()
            failure = None
            try:
                asyncio.run(synthesize(text, audio, **controls))
                synth_seconds = time.perf_counter() - started
                duration = audio_duration(audio)
            except Exception as exc:
                synth_seconds = time.perf_counter() - started
                duration = None
                failure = f"{type(exc).__name__}: {exc}"
            after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            peak_mb = max(before, after) / 1024.0 if platform.system() != "Darwin" else max(before, after) / (1024.0 * 1024.0)
            results.append({
                "sample_id": f"sample_{sample_id}", "engine": engine, "case_id": case["id"],
                "expected_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "audio_path": str(audio) if audio.exists() else None,
                "measurement": {
                    "synthesis_seconds": round(synth_seconds, 6),
                    "audio_duration_seconds": round(duration, 6) if duration else None,
                    "rtf": round(synth_seconds / duration, 6) if duration else None,
                    "peak_ram_mb": round(peak_mb, 3),
                    "artifact_bytes": audio.stat().st_size if audio.exists() else None,
                    "failure_count": 1 if failure else 0, "retry_count": 0, "gpu_used": False,
                },
                "failure": failure,
            })
    report = {
        "schema_version": "1.0", "milestone": "M6.0", "voice": VOICE,
        "production_changed": False, "paid_services_used": False,
        "runner": {"platform": platform.platform(), "python": platform.python_version()},
        "wall_seconds": round(time.perf_counter() - started_all, 6), "samples": results,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "edge_results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    failures = [r for r in results if r["failure"]]
    if failures:
        raise RuntimeError(f"Edge benchmark failed for {len(failures)} samples")
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--corpus", type=Path, default=Path("docs/m6/benchmark_corpus.json"))
    p.add_argument("--out", type=Path, default=Path("artifacts/m6/edge"))
    args = p.parse_args()
    report = run(args.corpus, args.out)
    print(f"PASS: {len(report['samples'])} Edge samples; {report['wall_seconds']}s wall time")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
