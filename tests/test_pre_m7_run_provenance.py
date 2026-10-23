"""PRE-M7 active-run provenance selection: no network, secrets, or publishing."""
from pathlib import Path
import hashlib
import json

import pytest

from scripts.m6_run_provenance import select_run_artifact, stamp_json_artifact, verify_visual_chain, verify_render_chain, verify_package_chain


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
    video = (root / "video_agent.py").read_text(encoding="utf-8")
    qc = (root / "qc_agent.py").read_text(encoding="utf-8")
    assert "verify_visual_chain(OUTPUT_DIR, timestamp)" in video
    assert "verify_render_chain(OUTPUT_DIR, timestamp)" in qc

@pytest.fixture
def bound_render_chain(bound_visual_chain):
    folder, _, assets, _ = bound_visual_chain
    stamp = "20261023T120000Z"
    voice = folder / f"voice_{stamp}.wav"
    voice.write_bytes(b"qualified-fixture-voice")
    captions = folder / f"captions_{stamp}.srt"
    captions.write_text("1\\n00:00:00,000 --> 00:00:01,000\\nTest\\n", encoding="utf-8")
    final = folder / f"final_{stamp}.mp4"
    final.write_bytes(b"qualified-fixture-video")
    renderer = folder / f"renderer_manifest_{stamp}.json"
    renderer_data = stamp_json_artifact(
        {"schema_version": 2, "milestone": "M5.4", "timestamp": stamp, "segments": []},
        "pre-m7.renderer.v1", "agents.video_agent", stamp,
        (assets, voice, captions, final),
    )
    renderer.write_text(json.dumps(renderer_data), encoding="utf-8")
    visual_qc = folder / f"visual_qc_report_{stamp}.json"
    visual_qc.write_text('{"status":"PASS"}', encoding="utf-8")
    selection = folder / f"visual_selection_report_{stamp}.md"
    selection.write_text("Fixture-only visual selection", encoding="utf-8")
    qc = folder / f"qc_report_{stamp}.json"
    qc_data = stamp_json_artifact(
        {"schema_version": 2, "milestone": "M5.5", "status": "PASS", "timestamp": stamp},
        "pre-m7.qc.v1", "agents.qc_agent", stamp,
        (renderer, final, visual_qc, selection),
    )
    qc.write_text(json.dumps(qc_data), encoding="utf-8")
    return folder, voice, captions, final, renderer, qc, visual_qc, selection


def test_bound_render_and_package_chains_accept_exact_bytes(bound_render_chain):
    folder = bound_render_chain[0]
    verify_render_chain(folder, "20261023T120000Z")
    verify_package_chain(folder, "20261023T120000Z")


@pytest.mark.parametrize("index", [1, 2, 3])
def test_bound_renderer_rejects_stale_voice_captions_mp4(bound_render_chain, index):
    path = bound_render_chain[index]
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(SystemExit, match="upstream source digest mismatch"):
        verify_render_chain(bound_render_chain[0], "20261023T120000Z")


@pytest.mark.parametrize("field,bad", [
    ("producer", "agents.untrusted_video"),
    ("contract", "pre-m7.qc.v1"),
    ("run_timestamp", "20261024T120000Z"),
])
def test_bound_renderer_rejects_wrong_identity(bound_render_chain, field, bad):
    path = bound_render_chain[4]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["artifact_provenance"][field] = bad
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="provenance mismatch"):
        verify_render_chain(bound_render_chain[0], "20261023T120000Z")


@pytest.mark.parametrize("index", [4, 6, 7])
def test_bound_package_rejects_changed_renderer_visual_qc_selection(bound_render_chain, index):
    path = bound_render_chain[index]
    path.write_bytes(path.read_bytes() + (b"\n" if index == 4 else b"tamper"))
    with pytest.raises(SystemExit, match="upstream source digest mismatch|content digest mismatch"):
        verify_package_chain(bound_render_chain[0], "20261023T120000Z")


def test_bound_package_rejects_qc_status_substitution(bound_render_chain):
    path = bound_render_chain[5]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["status"] = "PASS_FROM_OTHER_RUN"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SystemExit, match="content digest mismatch"):
        verify_package_chain(bound_render_chain[0], "20261023T120000Z")


def test_renderer_qc_and_package_producers_enforce_bound_chain():
    root = Path(__file__).resolve().parents[1]
    video = (root / "agents/video_agent.py").read_text(encoding="utf-8")
    qc = (root / "agents/qc_agent.py").read_text(encoding="utf-8")
    package = (root / "scripts/m6_production_package_gate.py").read_text(encoding="utf-8")
    assert 'stamp_json_artifact(renderer_payload, "pre-m7.renderer.v1"' in video
    assert 'verify_render_chain(OUTPUT_DIR, timestamp)' in qc
    assert 'stamp_json_artifact(report, "pre-m7.qc.v1"' in qc
    assert "verify_package_chain(output_dir, timestamp)" in package
