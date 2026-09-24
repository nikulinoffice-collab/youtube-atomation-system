import json
from pathlib import Path

import pytest

from scripts.m6_production_route import active_backend, load_route, rollback_backend


def write_route(tmp_path: Path, **changes) -> Path:
    data = {
        "schema_version": 1,
        "active_backend": "m6-ryan",
        "rollback_backend": "edge",
        "rollback_voice": "en-US-GuyNeural",
        "migration": "M6.9",
        "publishing_enabled": False,
    }
    data.update(changes)
    path = tmp_path / "route.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_production_route_is_ryan_with_explicit_edge_rollback(tmp_path):
    path = write_route(tmp_path)
    assert active_backend(path) == "m6-ryan"
    assert rollback_backend(path) == "edge"


@pytest.mark.parametrize(
    "changes,error",
    [
        ({"active_backend": "edge"}, "PRODUCTION_ROUTE_RYAN_NOT_ACTIVE"),
        ({"rollback_backend": "m6-ryan"}, "PRODUCTION_ROUTE_ROLLBACK_NOT_DISTINCT"),
        ({"rollback_voice": "other"}, "PRODUCTION_ROUTE_ROLLBACK_IDENTITY_MISMATCH"),
        ({"publishing_enabled": True}, "PRODUCTION_ROUTE_PUBLISHING_MUST_REMAIN_DISABLED"),
    ],
)
def test_invalid_or_unsafe_route_fails_closed(tmp_path, changes, error):
    with pytest.raises(ValueError, match=error):
        load_route(write_route(tmp_path, **changes))
