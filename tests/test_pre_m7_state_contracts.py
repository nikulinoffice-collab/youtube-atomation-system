import json
from pathlib import Path

import pytest

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


@pytest.fixture
def isolated_history(monkeypatch, tmp_path: Path) -> Path:
    state_dir = tmp_path / "state"
    history_file = state_dir / "recent_topics.json"
    monkeypatch.setattr(script_agent, "STATE_DIR", state_dir)
    monkeypatch.setattr(script_agent, "HISTORY_FILE", history_file)
    state_dir.mkdir()
    return history_file


def test_restored_history_prevents_reusing_a_prior_article(isolated_history: Path):
    old_link = "https://example.test/previous"
    new_link = "https://example.test/new"
    isolated_history.write_text(json.dumps([old_link]))
    assert script_agent.load_recent_topics() == [old_link]
    articles = [{"link": old_link}, {"link": new_link}]
    assert script_agent.pick_unused_article(articles, script_agent.load_recent_topics()) == articles[1]
    script_agent.save_recent_topic(new_link)
    assert json.loads(isolated_history.read_text()) == [old_link, new_link]


def test_explicitly_empty_history_is_valid(isolated_history: Path):
    isolated_history.write_text("[]")
    assert script_agent.load_recent_topics() == []


def test_missing_history_is_only_a_bootstrap_state_at_python_layer(isolated_history: Path):
    assert not isolated_history.exists()
    assert script_agent.load_recent_topics() == []


@pytest.mark.parametrize(
    "invalid",
    ['{broken', '{}', 'null', '"https://example.test/story"',
     '[123]', '[""]', '[null]', '["https://example.test/ok", {}]'],
)
def test_corrupt_or_wrong_schema_restored_history_fails_closed(
    isolated_history: Path, invalid: str
):
    isolated_history.write_text(invalid)
    with pytest.raises(SystemExit, match="Recent-topic state"):
        script_agent.load_recent_topics()
    assert isolated_history.read_text() == invalid


def test_draft_workflow_requires_cache_continuity_and_saves_after_script():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "publish.yml"
    ).read_text()
    assert "permissions:\\n  contents: read" in workflow
    assert "contents: write" not in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" in workflow
    assert "cache-matched-key" in workflow
    assert "TOPIC_HISTORY_CACHE_MISS_FAIL_CLOSED" in workflow
    assert "bootstrap_topic_history:" in workflow
    assert "default: false" in workflow
    assert "test -f agents/state/recent_topics.json" in workflow
    restore = workflow.index("uses: actions/cache/restore@v4")
    continuity = workflow.index("name: Require restored history or explicit bootstrap")
    script = workflow.index("name: Generate script and update topic history")
    save = workflow.index("uses: actions/cache/save@v4")
    voice = workflow.index("python voice_agent.py")
    assert restore < continuity < script < save < voice
