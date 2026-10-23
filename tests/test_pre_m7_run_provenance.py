"""PRE-M7 active-run provenance selection: no network, secrets, or publishing."""
from pathlib import Path
import hashlib
import json

import pytest

from scripts.m6_run_provenance import select_run_artifact, stamp_json_artifact, verify_visual_chain


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


@pytest.fixture
def bound_chain(artifacts, monkeypatch):
    folder, script_path = artifacts
    stamp = "20261023T120000Z"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("FACTORY_RUN_TIMESTAMP", stamp)
    timeline_path = folder / f"narration_timeline_{stamp}.json"
    timeline = stamp_json_artifact(
        {"schema_version": 3, "text": "Verified narration", "words": []},
        "pre-m7.timeline.v1", "agents.voice_agent", stamp, (script_path,),
    )
    timeline_path.write_text(json.dumps(timeline), encoding="utf-8")
    storyboard_path = folder / f"storyboard_{stamp}.json"
    storyboard = stamp_json_artifact(
        {"schema_version": 3, "scene_count": 1, "scenes": [{"scene_id": 1}]},
        "pre-m7.storyboard.v1", "agents.storyboard_agent", stamp, (timeline_path,),
    )
    storyboard_path.write_text(json.dumps(storyboard), encoding="utf-8")
    return folder, script_path, timeline_path, storyboard_path


def test_bound_chain_accepts_only_exact_upstream_content(bound_chain):
    folder, _, timeline, storyboard = bound_chain
    assert select_run_artifact(folder, "narration_timeline_", "narration_timeline_*.json") == timeline
    assert select_run_artifact(folder, "storyboard_", "storyboard_*.json") == storyboard


@pytest.mark.parametrize("artifact_index,prefix,field,value", [
    (2, "narration_timeline_", "producer", "agents.fake_voice"),
    (2, "narration_timeline_", "contract", "pre-m7.script.v1"),
    (2, "narration_timeline_", "run_timestamp", "20261024T120000Z"),
    (3, "storyboard_", "producer", "agents.fake_storyboard"),
    (3, "storyboard_", "contract", "pre-m7.timeline.v1"),
    (3, "storyboard_", "run_timestamp", "20261024T120000Z"),
])
def test_bound_chain_rejects_wrong_producer_schema_run(
    bound_chain, artifact_index, prefix, field, value
):
    folder = bound_chain[0]
    path = bound_chain[artifact_index]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["artifact_provenance"][field] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="producer/schema/run provenance mismatch"):
        select_run_artifact(folder, prefix, prefix + "*.json")


@pytest.mark.parametrize("artifact_index,prefix", [
    (2, "narration_timeline_"), (3, "storyboard_"),
])
def test_bound_chain_rejects_payload_tampering(bound_chain, artifact_index, prefix):
    folder = bound_chain[0]
    path = bound_chain[artifact_index]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["restored_wrong_run_payload"] = True
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="content digest mismatch"):
        select_run_artifact(folder, prefix, prefix + "*.json")


@pytest.mark.parametrize("source_index,prefix", [
    (1, "narration_timeline_"), (2, "storyboard_"),
])
def test_bound_chain_rejects_stale_upstream_bytes(bound_chain, source_index, prefix):
    folder = bound_chain[0]
    source = bound_chain[source_index]
    source.write_bytes(source.read_bytes() + b"\\n")
    with pytest.raises(SystemExit, match="upstream source digest mismatch"):
        select_run_artifact(folder, prefix, prefix + "*.json")


def test_bound_chain_rejects_missing_upstream_source(bound_chain):
    folder, _, timeline, _ = bound_chain
    timeline.unlink()
    with pytest.raises(SystemExit, match="Missing or duplicate upstream provenance source"):
        select_run_artifact(folder, "storyboard_", "storyboard_*.json")


def test_bound_chain_rejects_restored_cache_provenance_swap(bound_chain):
    folder, _, _, storyboard = bound_chain
    data = json.loads(storyboard.read_text(encoding="utf-8"))
    data["artifact_provenance"]["sources"] = {"narration_timeline_20261024T120000Z.json": "0" * 64}
    storyboard.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="upstream source digest mismatch"):
        select_run_artifact(folder, "storyboard_", "storyboard_*.json")


def test_producers_stamp_timeline_and_storyboard_contracts():
    root = Path(__file__).resolve().parents[1] / "agents"
    for name, contract in (
        ("voice_agent.py", "pre-m7.timeline.v1"),
        ("storyboard_agent.py", "pre-m7.storyboard.v1"),
    ):
        source = (root / name).read_text(encoding="utf-8")
        assert "stamp_json_artifact(" in source
        assert contract in source

@pytest.fixture
def bound_visual_chain(bound_chain):
    folder, _, _, storyboard = bound_chain
    stamp = "20261023T120000Z"
    media = folder / f"visual_{stamp}_scene_01.jpg"
    media.write_bytes(b"verified-test-image-bytes")
    candidates = folder / f"candidate_manifest_{stamp}.json"
    candidate_data = stamp_json_artifact(
        {"schema_version": 2, "milestone": "M5.3",
         "source_storyboard": storyboard.name, "scenes": [{"scene_id": 1}]},
        "pre-m7.candidates.v1", "agents.visuals_m53_agent", stamp, (storyboard,),
    )
    candidates.write_text(json.dumps(candidate_data), encoding="utf-8")
    assets = folder / f"asset_manifest_{stamp}.json"
    asset_data = stamp_json_artifact(
        {"schema_version": 4, "source_storyboard": storyboard.name,
         "source_candidate_manifest": candidates.name,
         "assets": [{"scene_id": 1, "path": str(media)}]},
        "pre-m7.assets.v1", "agents.visuals_m53_agent",
        stamp, (candidates, media),
    )
    assets.write_text(json.dumps(asset_data), encoding="utf-8")
    return folder, candidates, assets, media


def test_bound_visual_chain_accepts_exact_candidate_and_media_bytes(bound_visual_chain):
    verify_visual_chain(bound_visual_chain[0], "20261023T120000Z")


@pytest.mark.parametrize("index,field,bad", [
    (1, "producer", "agents.other_visuals"),
    (1, "contract", "pre-m7.assets.v1"),
    (1, "run_timestamp", "20261024T120000Z"),
    (2, "producer", "agents.other_visuals"),
    (2, "contract", "pre-m7.candidates.v1"),
    (2, "run_timestamp", "20261024T120000Z"),
])
def test_bound_visual_chain_rejects_wrong_producer_schema_run(bound_visual_chain, index, field, bad):
    path = bound_visual_chain[index]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["artifact_provenance"][field] = bad
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="provenance mismatch"):
        verify_visual_chain(bound_visual_chain[0], "20261023T120000Z")


@pytest.mark.parametrize("index", [1, 2])
def test_bound_visual_chain_rejects_manifest_payload_tampering(bound_visual_chain, index):
    path = bound_visual_chain[index]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["restored_wrong_run"] = True
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="content digest mismatch"):
        verify_visual_chain(bound_visual_chain[0], "20261023T120000Z")


def test_bound_visual_chain_rejects_modified_media_bytes(bound_visual_chain):
    media = bound_visual_chain[3]
    media.write_bytes(b"restored-cache-contamination")
    with pytest.raises(SystemExit, match="upstream source digest mismatch"):
        verify_visual_chain(bound_visual_chain[0], "20261023T120000Z")


def test_bound_visual_chain_rejects_stale_storyboard_bytes(bound_visual_chain):
    storyboard = bound_visual_chain[0] / "storyboard_20261023T120000Z.json"
    storyboard.write_bytes(storyboard.read_bytes() + b"\n")
    with pytest.raises(SystemExit, match="upstream source digest mismatch"):
        verify_visual_chain(bound_visual_chain[0], "20261023T120000Z")


def test_bound_visual_chain_rejects_media_path_traversal(bound_visual_chain):
    path = bound_visual_chain[2]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["assets"][0]["path"] = "../wrong-run/visual.jpg"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="path escapes active-run"):
        verify_visual_chain(bound_visual_chain[0], "20261023T120000Z")


def test_visual_provenance_is_produced_and_enforced_before_render_qc():
    root = Path(__file__).resolve().parents[1] / "agents"
    producer = (root / "visuals_m53_agent.py").read_text(encoding="utf-8")
    assert "pre-m7.candidates.v1" in producer and "pre-m7.assets.v1" in producer
    assert producer.count("stamp_json_artifact(") == 2
    for name in ("video_agent.py", "qc_agent.py"):
        source = (root / name).read_text(encoding="utf-8")
        assert "verify_visual_chain(OUTPUT_DIR, timestamp)" in source
