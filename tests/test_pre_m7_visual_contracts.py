"""Fail-closed M5.4 visual contract regressions; no network or publishing."""
from __future__ import annotations

import inspect
import sys
import types
from pathlib import Path

import pytest

from agents import video_agent as video


def test_headline_compaction_and_publisher_identity():
    long_title = "A carefully sourced headline " * 12
    compact = video.compact_headline(long_title)
    assert compact.endswith("…") and len(compact) <= 117
    assert video.compact_headline("Short title") == "Short title"
    assert video.source_publisher("https://www.example.com/story") == ("EXAMPLE", "example.com")


@pytest.mark.parametrize("url", ["", "javascript:alert(1)", "file:///tmp/unsafe", "//missing-scheme.example"])
def test_mandatory_source_article_rejects_invalid_url_before_render(monkeypatch, url):
    monkeypatch.setattr(video, "render_source_card", lambda *args: pytest.fail("must not render invalid source"))
    with pytest.raises(SystemExit, match="valid source_url"):
        video.prepare_render_assets(
            [{"scene_id": 1, "provider": "source_article", "path": "screenshot.jpg", "source_url": url,
              "type": "image", "preferred_motion": "static"}], {}, "T"
        )


def test_source_card_transform_retains_original_asset_and_static_motion(monkeypatch, tmp_path):
    card = tmp_path / "card.jpg"
    card.write_bytes(b"card")
    monkeypatch.setattr(video, "render_source_card", lambda script, asset, timestamp: card)
    source = {"scene_id": 1, "provider": "source_article", "path": "original.png",
              "source_url": "https://example.com/story", "type": "image", "preferred_motion": "static"}
    original = dict(source)
    prepared = video.prepare_render_assets([source], {"source_title": "Test"}, "T")[0]
    assert source == original
    assert prepared["original_asset_path"] == "original.png"
    assert prepared["path"] == str(card)
    assert prepared["type"] == "image"
    assert prepared["preferred_motion"] == "static"
    assert prepared["render_transform"] == "concise_caption_safe_source_card"


def test_source_card_failure_never_downgrades_to_stock(monkeypatch):
    def fail(*args):
        raise SystemExit("Playwright unavailable")
    monkeypatch.setattr(video, "render_source_card", fail)
    with pytest.raises(SystemExit, match="Playwright unavailable"):
        video.prepare_render_assets([{"scene_id": 1, "provider": "source_article",
            "path": "stock-fallback.jpg", "source_url": "https://example.com/story",
            "type": "image", "preferred_motion": "static"}], {}, "T")


def test_source_card_html_is_escaped_and_caption_safe(monkeypatch, tmp_path):
    captured = {}
    class Page:
        def set_content(self, document, wait_until):
            captured["html"] = document
            assert wait_until == "load"
        def screenshot(self, path, type, quality):
            assert type == "jpeg" and quality == 92
            Path(path).write_bytes(b"nonempty-fixture")
    class Browser:
        def new_page(self, viewport):
            captured["viewport"] = viewport
            return Page()
        def close(self):
            captured["closed"] = True
    class Playwright:
        chromium = types.SimpleNamespace(launch=lambda: Browser())
    class Context:
        def __enter__(self):
            return Playwright()
        def __exit__(self, *args):
            return False
    fake_pkg = types.ModuleType("playwright")
    fake_api = types.ModuleType("playwright.sync_api")
    fake_api.sync_playwright = lambda: Context()
    monkeypatch.setitem(sys.modules, "playwright", fake_pkg)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_api)
    monkeypatch.setattr(video, "OUTPUT_DIR", tmp_path)
    card = video.render_source_card({"source_title": "A & B <C>", "source_date": "2026-10-23"},
        {"scene_id": 1, "source_url": "https://www.example.com/article"}, "T")
    assert card.exists() and card.stat().st_size > 0
    assert captured["viewport"] == {"width": 1080, "height": 1920}
    assert "&amp;" in captured["html"] and "&lt;C&gt;" in captured["html"]
    assert "height:520px" in captured["html"]
    assert "example.com" in captured["html"] and captured["closed"]


@pytest.mark.parametrize("motion", ["static", "slow_push_in", "slow_pull_out", "pan_left", "pan_right"])
def test_still_motion_filter_preserves_each_visual_direction(motion):
    filt = video.still_motion_filter(0, 0.4, 12, motion)
    assert "1080:1920" in filt and "trim=0:0.400" in filt
    assert "setpts=PTS-STARTPTS" in filt
    if motion == "static":
        assert "zoompan=" not in filt
    else:
        assert "zoompan=" in filt
        assert "s=1080x1920:fps=30" in filt
    if motion == "slow_push_in":
        assert "zoom+0.0013" in filt
    elif motion == "slow_pull_out":
        assert "zoom-0.0013" in filt
    elif motion == "pan_left":
        assert "1-on/11" in filt
    elif motion == "pan_right":
        assert "on/11" in filt


def test_unknown_motion_fails_closed():
    with pytest.raises(SystemExit, match="Unsupported still motion"):
        video.still_motion_filter(0, 1.0, 30, "unapproved")


def test_visuals_command_preserves_native_video_and_applies_still_motion(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(video, "run", lambda command: commands.append(command))
    video.build_visuals_segment([
        {"asset_path": "still.jpg", "asset_type": "image", "render_duration": 0.4,
         "resolved_motion": "slow_push_in"},
        {"asset_path": "clip.mp4", "asset_type": "video", "render_duration": 0.4,
         "resolved_motion": "native_video"},
    ], tmp_path / "silent.mp4")
    assert len(commands) == 1
    cmd = commands[0]
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "zoompan=" in graph and "concat=n=2:v=1:a=0" in graph
    assert "[1:v]trim=0:0.400" in graph
    assert "-stream_loop" in cmd and "clip.mp4" in cmd


def test_m69_voice_media_resolver_is_still_fail_closed():
    source = inspect.getsource(video.main)
    assert "resolve_voice_artifact(OUTPUT_DIR,timestamp)" in source
    assert "except ProductionMediaError" in source
    assert "voice_path=OUTPUT_DIR" not in source
