"""Fail-closed M6.9 production package artifact gate.

This gate is intentionally backend-neutral: Ryan contributes one lossless WAV,
while the explicit Edge rollback route contributes one MP3.  A package with
both formats, neither format, or mismatched timestamped artifacts is rejected.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from scripts.m6_production_media import ProductionMediaError, resolve_voice_artifact

REQUIRED_PREFIXES = (
    "qc_report_",
    "renderer_manifest_",
    "narration_timeline_",
    "storyboard_",
    "asset_manifest_",
    "candidate_manifest_",
    "captions_",
    "final_",
)


def verify_production_package(output_dir: Path, timestamp: str) -> Path:
    output_dir = Path(output_dir)
    voice = resolve_voice_artifact(output_dir, timestamp)
    required = {
        "qc_report": output_dir / f"qc_report_{timestamp}.json",
        "renderer_manifest": output_dir / f"renderer_manifest_{timestamp}.json",
        "narration_timeline": output_dir / f"narration_timeline_{timestamp}.json",
        "storyboard": output_dir / f"storyboard_{timestamp}.json",
        "asset_manifest": output_dir / f"asset_manifest_{timestamp}.json",
        "candidate_manifest": output_dir / f"candidate_manifest_{timestamp}.json",
        "captions": output_dir / f"captions_{timestamp}.srt",
        "final": output_dir / f"final_{timestamp}.mp4",
    }
    missing = [name for name, path in required.items() if not path.exists() or path.stat().st_size <= 0]
    if missing:
        raise ProductionMediaError("MISSING_PRODUCTION_ARTIFACTS: " + ",".join(missing))
    return voice


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("agents/output"))
    parser.add_argument("--timestamp", required=True)
    args = parser.parse_args()
    voice = verify_production_package(args.output_dir, args.timestamp)
    print(f"M6_9_PRODUCTION_PACKAGE_PASS voice={voice.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
