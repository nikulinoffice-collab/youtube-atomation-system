"""M4 deterministic technical QC for Factory V1 artifacts.

Fails closed if the final render, narration timeline, storyboard, asset manifest,
renderer manifest, captions, or voice audio disagree on core timing/shape.
Writes qc_report_<timestamp>.json only after all checks pass.
"""

import json
import re
import subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
EXPECTED_WIDTH = 1080
EXPECTED_HEIGHT = 1920
EXPECTED_FPS = 30.0
DURATION_TOLERANCE = 0.25
BOUNDARY_TOLERANCE = 0.06


def latest_script() -> Path:
    matches = sorted(OUTPUT_DIR.glob("script_[0-9]*.json"))
    if not matches:
        raise SystemExit("No script artifact found for QC.")
    return matches[-1]


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid JSON artifact {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"JSON artifact {path.name} must contain an object.")
    return data


def ffprobe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"ffprobe failed for {path.name}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def rate_to_float(value: str) -> float:
    if "/" in value:
        num, den = value.split("/", 1)
        return float(num) / float(den)
    return float(value)


def srt_last_end(path: Path) -> float:
    text = path.read_text(encoding="utf-8")
    matches = re.findall(r"-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})", text)
    if not matches:
        raise SystemExit("Captions contain no SRT time ranges.")
    hh, mm, ss, ms = map(int, matches[-1])
    return hh * 3600 + mm * 60 + ss + ms / 1000.0


def require_file(path: Path) -> None:
    if not path.exists() or path.stat().st_size <= 0:
        raise SystemExit(f"Required artifact missing or empty: {path.name}")


def main() -> None:
    script_path = latest_script()
    timestamp = script_path.stem.replace("script_", "")
    paths = {
        "script": script_path,
        "voice": OUTPUT_DIR / f"voice_{timestamp}.mp3",
        "timeline": OUTPUT_DIR / f"narration_timeline_{timestamp}.json",
        "captions": OUTPUT_DIR / f"captions_{timestamp}.srt",
        "storyboard": OUTPUT_DIR / f"storyboard_{timestamp}.json",
        "assets": OUTPUT_DIR / f"asset_manifest_{timestamp}.json",
        "renderer": OUTPUT_DIR / f"renderer_manifest_{timestamp}.json",
        "final": OUTPUT_DIR / f"final_{timestamp}.mp4",
    }
    for path in paths.values():
        require_file(path)

    timeline = read_json(paths["timeline"])
    storyboard = read_json(paths["storyboard"])
    asset_manifest = read_json(paths["assets"])
    renderer = read_json(paths["renderer"])
    voice_probe = ffprobe(paths["voice"])
    final_probe = ffprobe(paths["final"])

    audio_duration = float(voice_probe["format"]["duration"])
    timeline_duration = float(timeline["duration"])
    final_duration = float(final_probe["format"]["duration"])
    caption_end = srt_last_end(paths["captions"])

    if abs(audio_duration - timeline_duration) > DURATION_TOLERANCE:
        raise SystemExit("Narration timeline duration does not match voice audio.")
    if abs(final_duration - audio_duration) > DURATION_TOLERANCE:
        raise SystemExit("Final MP4 duration does not match voice audio.")
    if caption_end > audio_duration + BOUNDARY_TOLERANCE:
        raise SystemExit("Captions extend past narration audio.")

    video_streams = [s for s in final_probe.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in final_probe.get("streams", []) if s.get("codec_type") == "audio"]
    if len(video_streams) != 1 or not audio_streams:
        raise SystemExit("Final MP4 must contain exactly one video stream and at least one audio stream.")
    video = video_streams[0]
    if int(video.get("width", 0)) != EXPECTED_WIDTH or int(video.get("height", 0)) != EXPECTED_HEIGHT:
        raise SystemExit("Final MP4 is not 1080x1920.")
    fps = rate_to_float(str(video.get("r_frame_rate", "0/1")))
    if abs(fps - EXPECTED_FPS) > 0.05:
        raise SystemExit(f"Unexpected final FPS: {fps}")

    scenes = storyboard.get("scenes", [])
    assets = asset_manifest.get("assets", [])
    segments = renderer.get("segments", [])
    if not (8 <= len(scenes) <= 12):
        raise SystemExit("Storyboard scene count outside certified 8..12 range.")
    if len(scenes) != len(assets) or len(scenes) != len(segments):
        raise SystemExit("Storyboard/assets/renderer scene counts disagree.")
    if renderer.get("strategy") != "storyboard_scene_start_cuts_with_previous_scene_pause_hold":
        raise SystemExit("Unexpected renderer timing strategy.")

    for index, (scene, asset, segment) in enumerate(zip(scenes, assets, segments)):
        scene_id = index + 1
        if int(scene["scene_id"]) != scene_id or int(asset["scene_id"]) != scene_id or int(segment["scene_id"]) != scene_id:
            raise SystemExit(f"Scene identity mismatch at position {scene_id}.")
        for field, source_value, rendered_value in (
            ("start", scene["start"], segment["scene_start"]),
            ("end", scene["end"], segment["scene_end"]),
        ):
            if abs(float(source_value) - float(rendered_value)) > BOUNDARY_TOLERANCE:
                raise SystemExit(f"Scene {scene_id} {field} drifted during rendering.")
        if str(asset["asset_id"]) != str(segment["asset_id"]):
            raise SystemExit(f"Scene {scene_id} renderer asset provenance mismatch.")
        if float(segment["render_duration"]) <= 0:
            raise SystemExit(f"Scene {scene_id} has non-positive render duration.")
        if float(segment["scene_start"]) < float(segment["render_start"]) - BOUNDARY_TOLERANCE:
            raise SystemExit(f"Scene {scene_id} semantic start precedes rendered segment.")
        if float(segment["scene_end"]) > float(segment["render_end"]) + BOUNDARY_TOLERANCE:
            raise SystemExit(f"Scene {scene_id} semantic end exceeds rendered segment.")

    if abs(float(segments[0]["render_start"])) > BOUNDARY_TOLERANCE:
        raise SystemExit("Rendered timeline does not start at zero.")
    if abs(float(segments[-1]["render_end"]) - audio_duration) > DURATION_TOLERANCE:
        raise SystemExit("Rendered timeline does not end with narration audio.")
    for left, right in zip(segments, segments[1:]):
        if abs(float(left["render_end"]) - float(right["render_start"])) > BOUNDARY_TOLERANCE:
            raise SystemExit("Rendered timeline has a gap or overlap.")

    report = {
        "schema_version": 1,
        "timestamp": timestamp,
        "status": "PASS",
        "checks": {
            "required_artifacts_present": True,
            "voice_matches_narration_timeline": True,
            "final_duration_matches_voice": True,
            "captions_within_narration": True,
            "final_resolution": f"{EXPECTED_WIDTH}x{EXPECTED_HEIGHT}",
            "final_fps": fps,
            "video_stream_present": True,
            "audio_stream_present": True,
            "storyboard_scene_count": len(scenes),
            "asset_count": len(assets),
            "renderer_segment_count": len(segments),
            "scene_timing_preserved": True,
            "asset_provenance_preserved": True,
            "render_timeline_contiguous": True,
        },
        "durations": {
            "timeline": timeline_duration,
            "voice": audio_duration,
            "captions_end": caption_end,
            "final": final_duration,
        },
        "artifacts": {key: path.name for key, path in paths.items()},
    }
    report_path = OUTPUT_DIR / f"qc_report_{timestamp}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ M4 QC PASS: {report_path.name}")
    print(json.dumps(report["checks"], indent=2))


if __name__ == "__main__":
    main()
