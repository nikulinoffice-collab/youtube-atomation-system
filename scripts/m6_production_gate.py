#!/usr/bin/env python3
"""M6.9 fail-closed production migration gate."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/m6/qwen3_ryan_frozen.json"

EXPECTED = {
    "model": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    "model_revision": "85e237c12c027371202489a0ec509ded67b5e4b5",
    "source_commit": "022e286b98fbec7e1e916cb940cdf532cd9f488e",
    "speaker": "Ryan",
    "language": "English",
}
EVIDENCE = {
    "runtime_candidate_sha": "b2e6a9a7bddbc34ff0ea025566d64d95c14157ef",
    "run_id": 35622794103,
    "job_id": 106409715089,
    "artifact_id": 10650630260,
}

class ProductionGateError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code

def qualify(approval, rollback, config_path=CONFIG):
    cfg = json.loads(Path(config_path).read_text())
    if approval.get("human_review_approved") is not True:
        raise ProductionGateError("HUMAN_REVIEW_REQUIRED", "M6.8 approval missing")
    if approval.get("publishing_rights_blocker") is not False:
        raise ProductionGateError("RIGHTS_BLOCKED", "rights review is not clear")
    for key, value in EVIDENCE.items():
        if approval.get(key) != value:
            raise ProductionGateError("EVIDENCE_MISMATCH", key)
    for key, value in EXPECTED.items():
        if cfg.get(key) != value:
            raise ProductionGateError("CONFIG_DRIFT", key)
    if cfg.get("paid_services") is not False:
        raise ProductionGateError("PAID_SERVICE_FORBIDDEN", "zero-cost invariant violated")
    if rollback.get("enabled") is not True or not rollback.get("target"):
        raise ProductionGateError("ROLLBACK_REQUIRED", "rollback target required")
    if rollback.get("automatic_on_failure") is not True:
        raise ProductionGateError("ROLLBACK_FAIL_OPEN", "automatic rollback required")
    return {
        "qualified": True,
        "voice": cfg["speaker"],
        "model_revision": cfg["model_revision"],
        "rollback_target": rollback["target"],
        "quality_configuration_changed": False,
    }
