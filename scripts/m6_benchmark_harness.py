#!/usr/bin/env python3
"""M6.0 benchmark harness.

This harness is deliberately engine-neutral. It validates the frozen corpus,
records reproducible runtime measurements supplied by engine-specific runners,
and creates opaque sample IDs for blind listening. It does not synthesize
speech, call paid services, or alter the production voice path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_ENGINES = (
    "edge_legacy",
    "edge_directed",
    "gemini_free",
    "chatterbox_nano",
    "moss_tts_nano",
    "kokoro",
)
REQUIRED_CASE_IDS = {
    "hook", "question", "contrast", "important_fact", "reveal", "neutral",
    "numbers_dates", "acronyms", "versions_units", "long_sentence",
    "paragraphs", "short_30s",
}
MEASUREMENT_FIELDS = (
    "dependency_install_seconds", "model_download_bytes", "cold_start_seconds",
    "synthesis_seconds", "audio_duration_seconds", "rtf", "peak_ram_mb",
    "artifact_bytes", "failure_count", "retry_count", "gpu_used",
)


def load_corpus(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise ValueError("corpus cases must be a list")
    ids = [case.get("id") for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("corpus case ids must be unique")
    missing = REQUIRED_CASE_IDS - set(ids)
    if missing:
        raise ValueError(f"corpus missing required cases: {sorted(missing)}")
    for case in cases:
        if not isinstance(case.get("text"), str) or not case["text"].strip():
            raise ValueError(f"case {case.get('id')} has empty text")
        if not isinstance(case.get("tests"), list) or not case["tests"]:
            raise ValueError(f"case {case.get('id')} has no tests")
    return data


def corpus_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(corpus_path: Path, seed: str | None = None) -> dict:
    corpus = load_corpus(corpus_path)
    salt = seed or secrets.token_hex(16)
    samples = []
    for engine in REQUIRED_ENGINES:
        for case in corpus["cases"]:
            digest = hashlib.sha256(f"{salt}:{engine}:{case['id']}".encode()).hexdigest()[:12]
            samples.append({
                "sample_id": f"sample_{digest}",
                "case_id": case["id"],
                "engine": engine,
                "expected_text_sha256": hashlib.sha256(case["text"].encode()).hexdigest(),
                "audio_path": None,
                "measurement": {field: None for field in MEASUREMENT_FIELDS},
            })
    return {
        "schema_version": "1.0",
        "milestone": "M6.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "corpus_sha256": corpus_sha256(corpus_path),
        "runner": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "machine": platform.machine(),
        },
        "production_changed": False,
        "paid_services_used": False,
        "engines": list(REQUIRED_ENGINES),
        "samples": samples,
    }


def validate_results(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    samples = data.get("samples", [])
    if len(samples) != len(REQUIRED_ENGINES) * len(REQUIRED_CASE_IDS):
        raise ValueError("result manifest does not contain the complete engine/case matrix")
    seen = set()
    for sample in samples:
        key = (sample.get("engine"), sample.get("case_id"))
        if key in seen:
            raise ValueError(f"duplicate result {key}")
        seen.add(key)
        measurement = sample.get("measurement") or {}
        missing = [field for field in MEASUREMENT_FIELDS if field not in measurement]
        if missing:
            raise ValueError(f"{key} missing measurement fields: {missing}")
        synth = measurement.get("synthesis_seconds")
        duration = measurement.get("audio_duration_seconds")
        rtf = measurement.get("rtf")
        if synth is not None and duration is not None:
            if duration <= 0:
                raise ValueError(f"{key} has non-positive audio duration")
            expected = synth / duration
            if rtf is None or abs(rtf - expected) > 1e-3:
                raise ValueError(f"{key} has inconsistent RTF")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("docs/m6/benchmark_corpus.json"))
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/m6/benchmark_manifest.json"))
    parser.add_argument("--seed", help="Deterministic test-only blinding seed; omit for real blind review")
    parser.add_argument("--validate-results", type=Path)
    args = parser.parse_args()

    if args.validate_results:
        validate_results(args.validate_results)
        print(f"PASS: {args.validate_results}")
        return 0

    manifest = build_manifest(args.corpus, args.seed)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(manifest['samples'])} blind benchmark slots to {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
