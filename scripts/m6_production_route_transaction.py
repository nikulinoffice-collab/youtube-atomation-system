"""Executable fail-closed M6.9 production route transaction.

This module changes only an explicit route-state JSON path.  It is intentionally
independent of publishing and synthesis.  A candidate Ryan route is committed
atomically only after pre-switch validation; a failed/exceptional post-switch
health check restores the exact prior Edge route atomically.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

RYAN = "m6-ryan"
EDGE = "edge"
EDGE_VOICE = "en-US-GuyNeural"


def _read(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("PRODUCTION_ROUTE_SCHEMA_MISMATCH")
    if data.get("active_backend") not in {RYAN, EDGE}:
        raise ValueError("PRODUCTION_ROUTE_UNKNOWN_BACKEND")
    if data.get("rollback_backend") != EDGE or data.get("rollback_voice") != EDGE_VOICE:
        raise ValueError("PRODUCTION_ROUTE_ROLLBACK_IDENTITY_MISMATCH")
    if data.get("publishing_enabled") is not False:
        raise ValueError("PRODUCTION_ROUTE_PUBLISHING_MUST_REMAIN_DISABLED")
    return data


def _atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def switch_ryan_with_health(
    path: Path,
    *,
    pre_switch_check: Callable[[dict], bool],
    health_check: Callable[[dict], bool],
) -> dict:
    """Switch Edge->Ryan transactionally and automatically restore Edge on health failure.

    The function requires an explicit Edge baseline.  A pre-switch failure does
    not write route state.  After the atomic Ryan switch, False or an exception
    from the health check causes restoration of the exact original JSON state.
    """
    original = _read(path)
    if original["active_backend"] != EDGE:
        raise ValueError("PRODUCTION_ROUTE_TRANSACTION_REQUIRES_EDGE_BASELINE")

    candidate = dict(original)
    candidate["active_backend"] = RYAN

    try:
        prepared = bool(pre_switch_check(dict(candidate)))
    except Exception:
        prepared = False
    if not prepared:
        if _read(path) != original:
            raise RuntimeError("PRODUCTION_ROUTE_PRE_SWITCH_MUTATION")
        return {
            "status": "PRE_SWITCH_ABORTED",
            "before": EDGE,
            "after": EDGE,
            "health_passed": False,
            "rollback_performed": False,
        }

    _atomic_write(path, candidate)
    if _read(path)["active_backend"] != RYAN:
        raise RuntimeError("PRODUCTION_ROUTE_SWITCH_NOT_COMMITTED")

    try:
        healthy = bool(health_check(dict(candidate)))
    except Exception:
        healthy = False

    if not healthy:
        _atomic_write(path, original)
        restored = _read(path)
        if restored != original or restored["active_backend"] != EDGE:
            raise RuntimeError("PRODUCTION_ROUTE_AUTOMATIC_ROLLBACK_FAILED")
        return {
            "status": "ROLLED_BACK",
            "before": EDGE,
            "after": EDGE,
            "health_passed": False,
            "rollback_performed": True,
        }

    final = _read(path)
    if final["active_backend"] != RYAN:
        raise RuntimeError("PRODUCTION_ROUTE_POST_HEALTH_STATE_MISMATCH")
    return {
        "status": "COMMITTED",
        "before": EDGE,
        "after": RYAN,
        "health_passed": True,
        "rollback_performed": False,
    }
