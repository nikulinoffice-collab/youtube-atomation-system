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


def test_edge_rollback_synthesis_path_executes(monkeypatch, tmp_path):
    """Rollback must execute without real network access and emit audio + boundaries."""
    import asyncio
    import sys
    from types import SimpleNamespace

    from agents import voice_agent

    class FakeCommunicate:
        def __init__(self, text, voice, rate, boundary):
            assert text == "Hello world"
            assert voice == voice_agent.VOICE
            assert rate == voice_agent.RATE
            assert boundary == "WordBoundary"

        async def stream(self):
            yield {"type": "audio", "data": b"fake-mp3"}
            yield {"type": "WordBoundary", "offset": 0, "duration": 5_000_000, "text": "Hello"}
            yield {"type": "WordBoundary", "offset": 5_000_000, "duration": 5_000_000, "text": "world"}

    monkeypatch.setitem(sys.modules, "edge_tts", SimpleNamespace(Communicate=FakeCommunicate))
    audio_path = tmp_path / "rollback.mp3"
    boundaries = asyncio.run(voice_agent.generate_voice_and_boundaries("Hello world", audio_path))

    assert audio_path.read_bytes() == b"fake-mp3"
    assert boundaries == [
        {"boundary_text": "Hello", "start": 0.0, "end": 0.5},
        {"boundary_text": "world", "start": 0.5, "end": 1.0},
    ]
