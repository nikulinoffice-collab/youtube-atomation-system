"""Build a deterministic M6.8 human-review manifest.

This package is evidence for human listening review. It never certifies naturalness
or permits M6.9 production migration.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

PACKAGE_VERSION = "m6.review-package.v1"
REQUIRED_ROLES = (
    "HOOK", "QUESTION", "CONTRAST", "IMPORTANT_FACT", "REVEAL",
    "EXPLANATION", "TRANSITION", "CONCLUSION",
)


class ReviewPackageError(ValueError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_review_manifest(*, audio_path: str | Path, plan: Mapping,
                          alignment: Mapping, qc: Mapping,
                          representative_cases: Sequence[Mapping]) -> dict:
    audio_path = Path(audio_path)
    if not audio_path.is_file():
        raise ReviewPackageError("review audio is missing")
    actual_sha = _sha256(audio_path)
    if actual_sha != qc.get("audit", {}).get("audio_sha256"):
        raise ReviewPackageError("QC/audio SHA-256 mismatch")
    if qc.get("status") != "HUMAN_REVIEW_REQUIRED_M6_8":
        raise ReviewPackageError("QC has not reached the M6.8 human-review gate")
    if qc.get("naturalness_claimed") is not False or qc.get("production_migration_permitted") is not False:
        raise ReviewPackageError("human/production gates must remain fail-closed")

    blocks = plan.get("blocks", [])
    if not blocks or qc.get("audit", {}).get("block_ids") != [b.get("block_id") for b in blocks]:
        raise ReviewPackageError("VoicePlan/QC block identity mismatch")
    roles = {str(b.get("role")) for b in blocks}
    if not set(REQUIRED_ROLES).issubset(roles):
        raise ReviewPackageError("complete Short must exercise all directed roles")

    words = alignment.get("word_timings", [])
    if not words:
        raise ReviewPackageError("alignment timings are missing")
    case_ids = [str(c.get("case_id", "")) for c in representative_cases]
    if not case_ids or any(not x for x in case_ids) or len(case_ids) != len(set(case_ids)):
        raise ReviewPackageError("representative case IDs must be non-empty and unique")

    manifest = {
        "version": PACKAGE_VERSION,
        "status": "HUMAN_REVIEW_REQUIRED_M6_8",
        "naturalness_claimed": False,
        "production_migration_permitted": False,
        "m6_9_autostart_permitted": False,
        "audio": {"path": audio_path.name, "sha256": actual_sha},
        "provenance": {
            "plan_version": str(plan.get("version")),
            "alignment_version": str(alignment.get("version")),
            "qc_version": str(qc.get("version")),
            "block_ids": [b["block_id"] for b in blocks],
        },
        "representative_cases": list(representative_cases),
        "human_review": {
            "required": True,
            "criteria": [
                "speaker/config continuity", "pronunciation", "semantic emphasis",
                "question/reveal contour", "controlled pacing and pauses",
                "restrained emotion", "overall naturalness",
            ],
        },
    }
    return manifest


def write_review_manifest(path: str | Path, manifest: Mapping) -> None:
    Path(path).write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
