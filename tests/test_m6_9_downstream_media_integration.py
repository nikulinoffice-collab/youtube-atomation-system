from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _source(name: str) -> str:
    return (ROOT / "agents" / name).read_text(encoding="utf-8")


def test_video_agent_uses_fail_closed_production_voice_resolver():
    source = _source("video_agent.py")
    assert "resolve_voice_artifact" in source
    assert 'voice_{timestamp}.mp3' not in source


def test_qc_agent_uses_fail_closed_production_voice_resolver():
    source = _source("qc_agent.py")
    assert "resolve_voice_artifact" in source
    assert 'voice_{timestamp}.mp3' not in source
