"""PRE-M7 active-run provenance selection: no network, secrets, or publishing."""
from pathlib import Path
import hashlib
import json

import pytest

from scripts.m6_run_provenance import select_run_artifact


def valid_script(stamp):
    data = {"title": "Verified story", "script": "A real source-backed test script.", "source_link": "https://example.org/source"}
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    data["artifact_provenance"] = {
        "contract": "pre-m7.script.v1",
        "producer": "agents.script_agent",
        "run_timestamp": stamp,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
    }
    return data


@pytest.fixture
def artifacts(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("FACTORY_RUN_TIMESTAMP", raising=False)
    earlier = tmp_path / "script_20261020T010101Z.json"
    current = tmp_path / "script_20261023T120000Z.json"
    wrong_newer = tmp_path / "script_20261024T120000Z.json"
    for path in (earlier, current, wrong_newer):
        path.write_text(json.dumps(valid_script(path.stem.removeprefix("script_"))), encoding="utf-8")
    return tmp_path, current


def test_active_run_rejects_lexicographically_newer_wrong_run(artifacts, monkeypatch):
    folder, current = artifacts
    monkeypatch.setenv("FACTORY_RUN_TIMESTAMP", "20261023T120000Z")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert select_run_artifact(folder, "script_", "script_*.json") == current


def test_missing_active_run_fails_closed_even_if_stale_artifacts_exist(artifacts, monkeypatch):
    folder, _ = artifacts
    monkeypatch.setenv("FACTORY_RUN_TIMESTAMP", "20261022T120000Z")
    with pytest.raises(SystemExit, match="Missing active-run artifact"):
        select_run_artifact(folder, "script_", "script_*.json")


@pytest.mark.parametrize("stamp", ["", "../other", "20261023", "20261023T120000Z.json", "20261023T120000Z/../../"])
def test_invalid_run_identity_fails_closed(artifacts, monkeypatch, stamp):
    folder, _ = artifacts
    monkeypatch.setenv("FACTORY_RUN_TIMESTAMP", stamp)
    with pytest.raises(SystemExit, match="Invalid FACTORY_RUN_TIMESTAMP"):
        select_run_artifact(folder, "script_", "script_*.json")


def test_actions_cannot_fallback_to_unbound_latest(artifacts, monkeypatch):
    folder, _ = artifacts
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(SystemExit, match="required in GitHub Actions"):
        select_run_artifact(folder, "script_", "script_*.json")


def test_local_only_compatibility_selection(artifacts):
    folder, _ = artifacts
    assert select_run_artifact(folder, "script_", "script_*.json").name == "script_20261024T120000Z.json"


@pytest.mark.parametrize("field,bad", [
    ("producer", "agents.other_agent"),
    ("contract", "pre-m7.storyboard.v1"),
    ("run_timestamp", "20261024T120000Z"),
])
def test_wrong_producer_schema_or_run_is_rejected(artifacts, monkeypatch, field, bad):
    folder, current = artifacts
    data = json.loads(current.read_text(encoding="utf-8"))
    data["artifact_provenance"][field] = bad
    current.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("FACTORY_RUN_TIMESTAMP", "20261023T120000Z")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(SystemExit, match="producer/schema/run provenance mismatch"):
        select_run_artifact(folder, "script_", "script_*.json")


def test_restored_script_content_tampering_fails_closed(artifacts, monkeypatch):
    folder, current = artifacts
    data = json.loads(current.read_text(encoding="utf-8"))
    data["script"] = "A stale or substituted script from another run."
    current.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("FACTORY_RUN_TIMESTAMP", "20261023T120000Z")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(SystemExit, match="content digest mismatch"):
        select_run_artifact(folder, "script_", "script_*.json")


def test_missing_digest_or_required_content_fails_closed(artifacts, monkeypatch):
    folder, current = artifacts
    monkeypatch.setenv("FACTORY_RUN_TIMESTAMP", "20261023T120000Z")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    data = json.loads(current.read_text(encoding="utf-8"))
    del data["artifact_provenance"]["payload_sha256"]
    current.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="digest missing or invalid"):
        select_run_artifact(folder, "script_", "script_*.json")


def test_invalid_json_from_restored_cache_fails_closed(artifacts, monkeypatch):
    folder, current = artifacts
    current.write_text("{corrupt", encoding="utf-8")
    monkeypatch.setenv("FACTORY_RUN_TIMESTAMP", "20261023T120000Z")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(SystemExit, match="Invalid script artifact JSON"):
        select_run_artifact(folder, "script_", "script_*.json")


@pytest.mark.parametrize("file_name", [
    "voice_agent.py", "captions_agent.py", "storyboard_agent.py",
    "visuals_agent.py", "video_agent.py", "qc_agent.py",
])
def test_all_critical_consumers_use_bound_selection(file_name):
    source = (Path(__file__).resolve().parents[1] / "agents" / file_name).read_text(encoding="utf-8")
    assert "from scripts.m6_run_provenance import select_run_artifact" in source
    assert "return select_run_artifact(" in source


def test_draft_workflow_exports_run_identity_before_downstream_processing():
    source = (Path(__file__).resolve().parents[1] / ".github/workflows/publish.yml").read_text(encoding="utf-8")
    export = source.index('print("FACTORY_RUN_TIMESTAMP=" + stamp)')
    voice = source.index("python voice_agent.py")
    assert export < voice
    assert 'if len(scripts) != 1:' in source
    assert 'python - <<\'PY\' >> "$GITHUB_ENV"' in source
