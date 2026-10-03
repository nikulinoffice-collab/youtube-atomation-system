import json
from pathlib import Path

from agents import script_agent


def test_topic_history_uses_canonical_state_directory():
    assert script_agent.HISTORY_FILE == script_agent.STATE_DIR / "recent_topics.json"
    assert script_agent.HISTORY_FILE.parent.name == "state"


def test_save_recent_topic_creates_state_directory(monkeypatch, tmp_path: Path):
    state_dir = tmp_path / "state"
    history_file = state_dir / "recent_topics.json"
    monkeypatch.setattr(script_agent, "STATE_DIR", state_dir)
    monkeypatch.setattr(script_agent, "HISTORY_FILE", history_file)

    script_agent.save_recent_topic("https://example.test/story")

    assert history_file.exists()
    assert json.loads(history_file.read_text()) == ["https://example.test/story"]
