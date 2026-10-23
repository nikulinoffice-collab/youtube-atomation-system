"""Fail-closed run-bound artifact selection for the draft production chain.

GitHub Actions must provide FACTORY_RUN_TIMESTAMP from the script generated in
the same run. Local interactive tools retain explicit legacy discovery only
outside Actions; production never selects a lexicographically newer wrong run.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

_RUN_STAMP = re.compile(r"[0-9]{8}T[0-9]{6}Z")


def select_run_artifact(output_dir: Path, prefix: str, pattern: str) -> Path:
    """Select the exact active-run artifact, never a different run's file."""
    raw = os.environ.get("FACTORY_RUN_TIMESTAMP")
    if raw is not None:
        if not _RUN_STAMP.fullmatch(raw):
            raise SystemExit("Invalid FACTORY_RUN_TIMESTAMP; refusing artifact discovery")
        selected = Path(output_dir) / f"{prefix}{raw}.json"
        if not selected.is_file():
            raise SystemExit(f"Missing active-run artifact {selected.name}; refusing stale fallback")
        return selected

    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        raise SystemExit("FACTORY_RUN_TIMESTAMP is required in GitHub Actions")

    # Explicit local-only compatibility path, never used by production Actions.
    matches = sorted(Path(output_dir).glob(pattern))
    if not matches:
        raise SystemExit(f"No {pattern} artifact found; run the upstream stage first")
    return matches[-1]
