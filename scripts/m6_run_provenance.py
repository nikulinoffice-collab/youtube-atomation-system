"""Fail-closed run-bound artifact selection for the draft production chain.

GitHub Actions must provide FACTORY_RUN_TIMESTAMP from the script generated in
the same run. Local interactive tools retain explicit legacy discovery only
outside Actions; production never selects a lexicographically newer wrong run.
"""
from __future__ import annotations

import os
import re
import json
import hashlib
from pathlib import Path

_RUN_STAMP = re.compile(r"[0-9]{8}T[0-9]{6}Z")


def verify_script_provenance(path: Path, run_timestamp: str) -> None:
    """Reject wrong producer/schema/run or modified restored script before TTS."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid script artifact JSON: {path.name}") from exc
    if not isinstance(data, dict):
        raise SystemExit("Script artifact must be a JSON object")
    identity = data.get("artifact_provenance")
    if not isinstance(identity, dict) or (
        identity.get("contract") != "pre-m7.script.v1"
        or identity.get("producer") != "agents.script_agent"
        or identity.get("run_timestamp") != run_timestamp
    ):
        raise SystemExit("Script artifact producer/schema/run provenance mismatch")
    if not all(isinstance(data.get(key), str) and data[key].strip()
               for key in ("script", "title", "source_link")):
        raise SystemExit("Script artifact required content is missing")
    digest = identity.get("payload_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise SystemExit("Script artifact content digest missing or invalid")
    payload = {key: value for key, value in data.items() if key != "artifact_provenance"}
    actual = hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()
    if actual != digest:
        raise SystemExit("Script artifact content digest mismatch")


def select_run_artifact(output_dir: Path, prefix: str, pattern: str) -> Path:
    """Select the exact active-run artifact, never a different run's file."""
    raw = os.environ.get("FACTORY_RUN_TIMESTAMP")
    if raw is not None:
        if not _RUN_STAMP.fullmatch(raw):
            raise SystemExit("Invalid FACTORY_RUN_TIMESTAMP; refusing artifact discovery")
        selected = Path(output_dir) / f"{prefix}{raw}.json"
        if not selected.is_file():
            raise SystemExit(f"Missing active-run artifact {selected.name}; refusing stale fallback")
        if prefix == "script_":
            verify_script_provenance(selected, raw)
        elif prefix in ("narration_timeline_", "storyboard_"):
            contract, producer, upstream_prefix = {
                "narration_timeline_": ("pre-m7.timeline.v1", "agents.voice_agent", "script_"),
                "storyboard_": ("pre-m7.storyboard.v1", "agents.storyboard_agent", "narration_timeline_"),
            }[prefix]
            upstream = Path(output_dir) / f"{upstream_prefix}{raw}.json"
            verify_json_artifact(selected, contract, producer, raw, (upstream,))
        return selected

    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        raise SystemExit("FACTORY_RUN_TIMESTAMP is required in GitHub Actions")

    # Explicit local-only compatibility path, never used by production Actions.
    matches = sorted(Path(output_dir).glob(pattern))
    if not matches:
        raise SystemExit(f"No {pattern} artifact found; run the upstream stage first")
    return matches[-1]


def _payload_digest(data: dict) -> str:
    payload = {key: value for key, value in data.items() if key != "artifact_provenance"}
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()


def _source_digests(paths) -> dict[str, str]:
    digests = {}
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file() or not path.name or path.name in digests:
            raise SystemExit(f"Missing or duplicate upstream provenance source: {path.name}")
        digests[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def stamp_json_artifact(data: dict, contract: str, producer: str,
                        run_timestamp: str, source_paths) -> dict:
    """Bind a produced JSON artifact to the exact active run and upstream bytes."""
    if not isinstance(data, dict) or not _RUN_STAMP.fullmatch(run_timestamp):
        raise SystemExit("Cannot stamp malformed run-bound artifact")
    if "artifact_provenance" in data:
        raise SystemExit("Refusing to overwrite existing artifact provenance")
    result = dict(data)
    result["artifact_provenance"] = {
        "contract": contract,
        "producer": producer,
        "run_timestamp": run_timestamp,
        "payload_sha256": _payload_digest(result),
        "sources": _source_digests(source_paths),
    }
    return result


def verify_json_artifact(path: Path, contract: str, producer: str,
                         run_timestamp: str, source_paths) -> None:
    """Reject wrong producer/schema/run, changed payload, or stale upstream bytes."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid run-bound artifact JSON: {path.name}") from exc
    if not isinstance(data, dict):
        raise SystemExit("Run-bound artifact must be a JSON object")
    identity = data.get("artifact_provenance")
    if not isinstance(identity, dict) or (
        identity.get("contract") != contract
        or identity.get("producer") != producer
        or identity.get("run_timestamp") != run_timestamp
    ):
        raise SystemExit("Run-bound artifact producer/schema/run provenance mismatch")
    if identity.get("payload_sha256") != _payload_digest(data):
        raise SystemExit("Run-bound artifact content digest mismatch")
    if identity.get("sources") != _source_digests(source_paths):
        raise SystemExit("Run-bound artifact upstream source digest mismatch")

def verify_visual_chain(output_dir: Path, run_timestamp: str) -> None:
    """Verify script -> storyboard -> ranked candidates -> media provenance."""
    if not _RUN_STAMP.fullmatch(run_timestamp):
        raise SystemExit("Invalid active run for visual provenance")
    output_dir = Path(output_dir)
    script = output_dir / f"script_{run_timestamp}.json"
    timeline = output_dir / f"narration_timeline_{run_timestamp}.json"
    storyboard = output_dir / f"storyboard_{run_timestamp}.json"
    candidates = output_dir / f"candidate_manifest_{run_timestamp}.json"
    assets_path = output_dir / f"asset_manifest_{run_timestamp}.json"
    verify_script_provenance(script, run_timestamp)
    verify_json_artifact(timeline, "pre-m7.timeline.v1", "agents.voice_agent",
                         run_timestamp, (script,))
    verify_json_artifact(storyboard, "pre-m7.storyboard.v1", "agents.storyboard_agent",
                         run_timestamp, (timeline,))
    verify_json_artifact(candidates, "pre-m7.candidates.v1", "agents.visuals_m53_agent",
                         run_timestamp, (storyboard,))
    try:
        candidate_data = json.loads(candidates.read_text(encoding="utf-8"))
        asset_data = json.loads(assets_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit("Invalid visual provenance manifest JSON") from exc
    if (candidate_data.get("schema_version") != 2
            or candidate_data.get("milestone") != "M5.3"
            or candidate_data.get("source_storyboard") != storyboard.name):
        raise SystemExit("Visual candidate producer/schema/source contract mismatch")
    if (not isinstance(asset_data, dict)
            or asset_data.get("schema_version") != 4
            or asset_data.get("source_storyboard") != storyboard.name
            or asset_data.get("source_candidate_manifest") != candidates.name):
        raise SystemExit("Visual asset producer/schema/source contract mismatch")
    assets = asset_data.get("assets")
    if not isinstance(assets, list) or not assets:
        raise SystemExit("Visual asset provenance requires nonempty assets")
    media_paths = []
    for asset in assets:
        if not isinstance(asset, dict):
            raise SystemExit("Invalid visual asset provenance entry")
        path = Path(str(asset.get("path", "")))
        if (path.resolve().parent != output_dir.resolve()
                or not re.fullmatch(
                    rf"visual_{run_timestamp}_scene_[0-9]{{2}}(?:_source)?\.(?:jpg|mp4)",
                    path.name,
                )):
            raise SystemExit("Visual asset path escapes active-run provenance")
        if not path.is_file() or path.stat().st_size <= 0:
            raise SystemExit("Missing or empty visual provenance media")
        media_paths.append(path)
    verify_json_artifact(assets_path, "pre-m7.assets.v1", "agents.visuals_m53_agent",
                         run_timestamp, (candidates, *media_paths))

def verify_render_chain(output_dir: Path, run_timestamp: str) -> None:
    """Reject renderer or MP4 assembled from stale visual, voice, or caption bytes."""
    verify_visual_chain(output_dir, run_timestamp)
    from scripts.m6_production_media import resolve_voice_artifact, ProductionMediaError
    output_dir = Path(output_dir)
    try:
        voice = resolve_voice_artifact(output_dir, run_timestamp)
    except ProductionMediaError as exc:
        raise SystemExit(str(exc)) from exc
    assets = output_dir / f"asset_manifest_{run_timestamp}.json"
    captions = output_dir / f"captions_{run_timestamp}.srt"
    final = output_dir / f"final_{run_timestamp}.mp4"
    renderer = output_dir / f"renderer_manifest_{run_timestamp}.json"
    verify_json_artifact(renderer, "pre-m7.renderer.v1", "agents.video_agent",
                         run_timestamp, (assets, voice, captions, final))
    data = json.loads(renderer.read_text(encoding="utf-8"))
    if (data.get("schema_version") != 2 or data.get("milestone") != "M5.4"
            or data.get("timestamp") != run_timestamp):
        raise SystemExit("Renderer producer/schema/run contract mismatch")


def verify_package_chain(output_dir: Path, run_timestamp: str) -> None:
    """Require QC provenance over exact renderer, final MP4, and visual QC evidence."""
    verify_render_chain(output_dir, run_timestamp)
    output_dir = Path(output_dir)
    renderer = output_dir / f"renderer_manifest_{run_timestamp}.json"
    final = output_dir / f"final_{run_timestamp}.mp4"
    visual_qc = output_dir / f"visual_qc_report_{run_timestamp}.json"
    selection = output_dir / f"visual_selection_report_{run_timestamp}.md"
    qc = output_dir / f"qc_report_{run_timestamp}.json"
    verify_json_artifact(qc, "pre-m7.qc.v1", "agents.qc_agent",
                         run_timestamp, (renderer, final, visual_qc, selection))
    data = json.loads(qc.read_text(encoding="utf-8"))
    if (data.get("schema_version") != 2 or data.get("milestone") != "M5.5"
            or data.get("status") != "PASS" or data.get("timestamp") != run_timestamp):
        raise SystemExit("QC producer/schema/run/PASS contract mismatch")
