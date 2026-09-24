"""Fail-closed M6.9 production voice routing contract."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTE = ROOT / "config" / "m6" / "production_voice_route.json"
ALLOWED = {"m6-ryan", "edge"}


def load_route(path: Path = DEFAULT_ROUTE) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("PRODUCTION_ROUTE_SCHEMA_MISMATCH")
    active = data.get("active_backend")
    rollback = data.get("rollback_backend")
    if active not in ALLOWED or rollback not in ALLOWED:
        raise ValueError("PRODUCTION_ROUTE_UNKNOWN_BACKEND")
    if active == rollback:
        raise ValueError("PRODUCTION_ROUTE_ROLLBACK_NOT_DISTINCT")
    if active != "m6-ryan":
        raise ValueError("PRODUCTION_ROUTE_RYAN_NOT_ACTIVE")
    if rollback != "edge" or data.get("rollback_voice") != "en-US-GuyNeural":
        raise ValueError("PRODUCTION_ROUTE_ROLLBACK_IDENTITY_MISMATCH")
    if data.get("publishing_enabled") is not False:
        raise ValueError("PRODUCTION_ROUTE_PUBLISHING_MUST_REMAIN_DISABLED")
    return data


def active_backend(path: Path = DEFAULT_ROUTE) -> str:
    return str(load_route(path)["active_backend"])


def rollback_backend(path: Path = DEFAULT_ROUTE) -> str:
    return str(load_route(path)["rollback_backend"])


if __name__ == "__main__":
    print(active_backend())
