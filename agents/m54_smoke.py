"""Deterministic, non-network M5.4 renderer smoke certification.

Exercises every synthetic still-motion path and the local Source Card renderer
without calling Gemini, Pexels, upload_agent, or any publishing service.
"""

import json
import subprocess
from pathlib import Path

import video_agent


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr[-3000:] or f"Command failed: {' '.join(cmd)}")


def assert_video(path: Path, minimum_duration: float) -> None:
    probe = video_agent.probe_media(path)
    streams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    if not streams:
        raise SystemExit(f"No video stream in {path}")
    stream = streams[0]
    if int(stream.get("width", 0)) != video_agent.TARGET_WIDTH or int(stream.get("height", 0)) != video_agent.TARGET_HEIGHT:
        raise SystemExit(f"Unexpected smoke resolution: {stream.get('width')}x{stream.get('height')}")
    if float(probe.get("format", {}).get("duration", 0)) + 0.05 < minimum_duration:
        raise SystemExit(f"Smoke video too short: {probe.get('format', {}).get('duration')}")


def main() -> None:
    output = video_agent.OUTPUT_DIR
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / "_m54_smoke_fixture.jpg"
    rendered = output / "_m54_smoke_motion.mp4"
    source_card = output / "source_card_M54SMOKE_scene_99.jpg"

    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        "color=c=0x334455:s=1080x1920:d=0.1", "-frames:v", "1", str(fixture),
    ])
    if not fixture.exists() or fixture.stat().st_size <= 0:
        raise SystemExit("M5.4 smoke fixture was not created")

    motions = ["static", "slow_push_in", "slow_pull_out", "pan_left", "pan_right"]
    duration = 0.40
    segments = [
        {
            "asset_path": str(fixture),
            "asset_type": "image",
            "render_duration": duration,
            "resolved_motion": motion,
        }
        for motion in motions
    ]
    video_agent.build_visuals_segment(segments, rendered)
    assert_video(rendered, duration * len(motions) - 0.10)

    script = {
        "source_title": "A deliberately long technology headline used to prove that the M5.4 mobile source card truncates safely instead of colliding with subtitles near the bottom of a vertical Short",
        "source_date": "2026-09-14",
    }
    asset = {
        "scene_id": 99,
        "source_url": "https://example.com/articles/m54-source-card-smoke",
    }
    card = video_agent.render_source_card(script, asset, "M54SMOKE")
    if card != source_card or not card.exists() or card.stat().st_size <= 0:
        raise SystemExit("M5.4 Source Card smoke render failed")
    image_probe = video_agent.probe_media(card)
    image_streams = [s for s in image_probe.get("streams", []) if s.get("codec_type") == "video"]
    if not image_streams:
        raise SystemExit("Source Card has no image/video stream")
    image_stream = image_streams[0]
    if int(image_stream.get("width", 0)) != 1080 or int(image_stream.get("height", 0)) != 1920:
        raise SystemExit("Source Card dimensions are not 1080x1920")
    if video_agent.compact_headline(script["source_title"]) == script["source_title"]:
        raise SystemExit("Source Card long-headline compaction was not exercised")
    publisher, domain = video_agent.source_publisher(asset["source_url"])
    if publisher != "EXAMPLE" or domain != "example.com":
        raise SystemExit("Source Card publisher/domain derivation failed")

    report = {
        "milestone": "M5.4",
        "status": "PASS",
        "tested_still_motions": motions,
        "motion_smoke_duration": float(video_agent.probe_media(rendered)["format"]["duration"]),
        "source_card_resolution": "1080x1920",
        "source_card_caption_safe_bottom_px": 520,
        "network_calls": 0,
    }
    report_path = output / "m54_smoke_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    fixture.unlink(missing_ok=True)
    rendered.unlink(missing_ok=True)
    source_card.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
