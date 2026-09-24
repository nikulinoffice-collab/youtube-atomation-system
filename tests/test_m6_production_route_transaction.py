import json
from pathlib import Path

from scripts.m6_production_route_transaction import switch_ryan_with_health


def edge_route(tmp_path: Path) -> Path:
    path = tmp_path / "route.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_backend": "edge",
                "rollback_backend": "edge",
                "rollback_voice": "en-US-GuyNeural",
                "migration": "M6.9",
                "publishing_enabled": False,
            }
        ),
        encoding="utf-8",
    )
    return path


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_failure_before_switch_leaves_edge_active(tmp_path):
    path = edge_route(tmp_path)
    before = read(path)
    result = switch_ryan_with_health(
        path,
        pre_switch_check=lambda candidate: False,
        health_check=lambda candidate: (_ for _ in ()).throw(AssertionError("health must not run")),
    )
    assert result["status"] == "PRE_SWITCH_ABORTED"
    assert result["rollback_performed"] is False
    assert read(path) == before
    assert read(path)["active_backend"] == "edge"


def test_successful_health_commits_ryan_and_never_enables_publishing(tmp_path):
    path = edge_route(tmp_path)
    result = switch_ryan_with_health(
        path,
        pre_switch_check=lambda candidate: candidate["publishing_enabled"] is False,
        health_check=lambda candidate: candidate["active_backend"] == "m6-ryan",
    )
    state = read(path)
    assert result == {
        "status": "COMMITTED",
        "before": "edge",
        "after": "m6-ryan",
        "health_passed": True,
        "rollback_performed": False,
    }
    assert state["active_backend"] == "m6-ryan"
    assert state["rollback_backend"] == "edge"
    assert state["rollback_voice"] == "en-US-GuyNeural"
    assert state["publishing_enabled"] is False


def test_post_switch_health_failure_automatically_restores_exact_edge_state(tmp_path):
    path = edge_route(tmp_path)
    before = read(path)
    result = switch_ryan_with_health(
        path,
        pre_switch_check=lambda candidate: True,
        health_check=lambda candidate: False,
    )
    assert result["status"] == "ROLLED_BACK"
    assert result["rollback_performed"] is True
    assert read(path) == before
    assert read(path)["active_backend"] == "edge"


def test_post_switch_health_exception_also_rolls_back(tmp_path):
    path = edge_route(tmp_path)
    before = read(path)

    def broken_health(candidate):
        raise RuntimeError("simulated health failure")

    result = switch_ryan_with_health(
        path,
        pre_switch_check=lambda candidate: True,
        health_check=broken_health,
    )
    assert result["status"] == "ROLLED_BACK"
    assert result["rollback_performed"] is True
    assert read(path) == before
