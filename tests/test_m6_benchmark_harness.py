import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("m6_benchmark_harness", ROOT / "scripts" / "m6_benchmark_harness.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


def test_frozen_corpus_has_all_required_cases():
    corpus = mod.load_corpus(ROOT / "docs" / "m6" / "benchmark_corpus.json")
    assert mod.REQUIRED_CASE_IDS <= {case["id"] for case in corpus["cases"]}


def test_manifest_is_complete_and_deterministically_blinded():
    path = ROOT / "docs" / "m6" / "benchmark_corpus.json"
    first = mod.build_manifest(path, seed="fixture-seed")
    second = mod.build_manifest(path, seed="fixture-seed")
    assert len(first["samples"]) == len(mod.REQUIRED_ENGINES) * len(mod.REQUIRED_CASE_IDS)
    assert [s["sample_id"] for s in first["samples"]] == [s["sample_id"] for s in second["samples"]]
    assert len({s["sample_id"] for s in first["samples"]}) == len(first["samples"])
    assert first["production_changed"] is False
    assert first["paid_services_used"] is False


def test_result_validation_recomputes_rtf(tmp_path):
    path = ROOT / "docs" / "m6" / "benchmark_corpus.json"
    manifest = mod.build_manifest(path, seed="fixture-seed")
    for sample in manifest["samples"]:
        sample["measurement"]["synthesis_seconds"] = 2.0
        sample["measurement"]["audio_duration_seconds"] = 8.0
        sample["measurement"]["rtf"] = 0.25
    result = tmp_path / "results.json"
    result.write_text(json.dumps(manifest), encoding="utf-8")
    mod.validate_results(result)

    manifest["samples"][0]["measurement"]["rtf"] = 0.5
    result.write_text(json.dumps(manifest), encoding="utf-8")
    try:
        mod.validate_results(result)
    except ValueError as exc:
        assert "inconsistent RTF" in str(exc)
    else:
        raise AssertionError("invalid RTF must fail closed")
