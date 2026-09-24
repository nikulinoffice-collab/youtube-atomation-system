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


def test_renderer_manifest_preserves_visual_qc_source_card_contract():
    source = _source("video_agent.py")
    assert '"source_card_strategy":"concise_caption_safe_mobile_card"' in source


def test_production_workflow_does_not_require_mp3_for_ryan_route():
    source = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    assert "FACTORY_VOICE_BACKEND: m6-ryan" in source
    assert "voices=(agents/output/voice_[0-9]*.mp3)" not in source
