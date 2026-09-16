#!/usr/bin/env python3
"""M6.0 frozen-corpus sample binding harness.

This script does not synthesize audio. It fail-closes source provenance before an
engine-specific shadow benchmark and records cryptographically bound sample
metadata after synthesis. Production voice code is intentionally untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import wave
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "docs/m6/benchmark_corpus.json"
MANIFEST = ROOT / "docs/m6/frozen_corpus_manifest.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_sources() -> list[dict[str, Any]]:
    corpus = load_json(CORPUS)
    manifest = load_json(MANIFEST)
    if corpus.get("schema_version") != "1.0" or manifest.get("schema_version") != "1.0":
        raise SystemExit("unsupported M6.0 corpus/manifest schema")
    if manifest.get("source_blob_sha") is None:
        raise SystemExit("manifest missing source_blob_sha")

    cases = corpus.get("cases", [])
    bindings = manifest.get("cases", [])
    if not cases or len(cases) != len(bindings):
        raise SystemExit("corpus/manifest case count mismatch")
    by_id = {item["id"]: item for item in bindings}
    if len(by_id) != len(bindings):
        raise SystemExit("duplicate case id in manifest")

    verified: list[dict[str, Any]] = []
    for case in cases:
        case_id = case.get("id")
        text = case.get("text")
        if not isinstance(case_id, str) or not isinstance(text, str):
            raise SystemExit("invalid corpus case")
        binding = by_id.get(case_id)
        if binding is None:
            raise SystemExit(f"missing manifest binding: {case_id}")
        actual = sha256_bytes(text.encode("utf-8"))
        if actual != binding.get("text_sha256"):
            raise SystemExit(f"source hash mismatch: {case_id}")
        verified.append({"id": case_id, "text": text, "text_sha256": actual})

    if {x["id"] for x in verified} != set(by_id):
        raise SystemExit("manifest contains unknown case id")
    return verified


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        if rate <= 0:
            raise SystemExit("invalid WAV sample rate")
        return frames / rate


def bind_sample(args: argparse.Namespace) -> dict[str, Any]:
    cases = {item["id"]: item for item in verify_sources()}
    if args.case_id not in cases:
        raise SystemExit(f"unknown case_id: {args.case_id}")
    audio = Path(args.audio)
    if not audio.is_file():
        raise SystemExit(f"audio not found: {audio}")
    if args.synthesis_seconds <= 0:
        raise SystemExit("synthesis_seconds must be > 0")
    if args.cold_or_warm not in {"cold", "warm"}:
        raise SystemExit("cold_or_warm must be cold or warm")

    duration = wav_duration(audio)
    if duration <= 0:
        raise SystemExit("audio duration must be > 0")
    config = json.loads(args.config_json)
    if not isinstance(config, dict):
        raise SystemExit("config_json must decode to an object")

    case = cases[args.case_id]
    return {
        "schema_version": "1.0",
        "milestone": "M6.0",
        "case_id": args.case_id,
        "source_text_sha256": case["text_sha256"],
        "engine_id": args.engine_id,
        "engine_version_or_commit": args.engine_version_or_commit,
        "config": config,
        "audio_sha256": sha256_file(audio),
        "audio_duration_seconds": round(duration, 6),
        "synthesis_seconds": round(args.synthesis_seconds, 6),
        "rtf": round(args.synthesis_seconds / duration, 6),
        "cold_or_warm": args.cold_or_warm,
        "production_changed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    bind = sub.add_parser("bind")
    bind.add_argument("--case-id", required=True)
    bind.add_argument("--engine-id", required=True)
    bind.add_argument("--engine-version-or-commit", required=True)
    bind.add_argument("--config-json", required=True)
    bind.add_argument("--audio", required=True)
    bind.add_argument("--synthesis-seconds", required=True, type=float)
    bind.add_argument("--cold-or-warm", required=True)
    bind.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.command == "verify":
        cases = verify_sources()
        print(json.dumps({"status": "PASS", "verified_cases": len(cases)}, sort_keys=True))
        return

    record = bind_sample(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "record": str(output), "rtf": record["rtf"]}, sort_keys=True))


if __name__ == "__main__":
    main()
