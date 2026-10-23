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
        return selected

    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        raise SystemExit("FACTORY_RUN_TIMESTAMP is required in GitHub Actions")

    # Explicit local-only compatibility path, never used by production Actions.
    matches = sorted(Path(output_dir).glob(pattern))
    if not matches:
        raise SystemExit(f"No {pattern} artifact found; run the upstream stage first")
    return matches[-1]
