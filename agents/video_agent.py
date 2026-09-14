"""M4 Storyboard-driven video renderer.

Consumes asset_manifest_<timestamp>.json as the canonical visual timeline.
Visual cuts occur at storyboard scene starts rather than by equal division.
A pause between spoken scenes keeps the preceding visual on screen; pre-roll
uses the first scene visual and post-roll uses the last scene visual. The
renderer writes renderer_manifest_<timestamp>.json so QC can prove exactly
which asset occupied every interval.
"""

import json
import random
import subprocess
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
MUSIC_DIR = Path(__file__).parent.parent / "assets" / "music"

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_FPS = 30
MUSIC_VOLUME = 0.12
TIMING_EPSILON = 0.050

SUBTITLE_STYLE = (
    "FontName=Arial,FontSize=16,Bold=1,PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
    "Alignment=2,MarginV=120"
)


def find_latest(pattern: str) -> Path:
    matches = sorted(OUTPUT_DIR.glob(pattern))
    if not matches:
        raise SystemExit(f"No files matching {pattern} in agents/output/. Run earlier steps first.")
    return matches[-1]


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-4000:])
        raise SystemExit(f"Command failed: {' '.join(cmd)}")


def probe_media(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=index,codec_type,width,height,r_frame_rate",
        "-of", "json", str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"ffprobe failed on {path}: {result.stderr}")
    return json.loads(result.stdout)


def get_audio_duration(audio_path: Path) -> float:
    return float(probe_media(audio_path)["format"]["duration"])


def escape_for_ffmpeg_filter(path: Path) -> str:
    value = str(path.resolve()).replace("\\", "/")
    return value.replace(":", "\\:")


def pick_random_music() -> Path | None:
    if not MUSIC_DIR.exists():
        return None
    tracks = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav"))
    return random.choice(tracks) if tracks else None


def validate_asset_manifest(manifest: dict) -> list[dict]:
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise SystemExit("asset_manifest has no assets.")
    if int(manifest.get("scene_count", -1)) != len(assets):
        raise SystemExit("asset_manifest scene_count mismatch.")

    previous_start = -1.0
    for expected_id, asset in enumerate(assets, start=1):
        if int(asset.get("scene_id", -1)) != expected_id:
            raise SystemExit("asset_manifest scenes must be ordered and contiguous from scene_id=1.")
        start = float(asset["scene_start"])
        end = float(asset["scene_end"])
        if start < 0 or end <= start or start <= previous_start:
            raise SystemExit(f"Invalid scene timing for scene {expected_id}: {start}..{end}")
        if not Path(str(asset["path"])).exists():
            raise SystemExit(f"Missing scene asset: {asset['path']}")
        if asset.get("type") not in {"video", "image"}:
            raise SystemExit(f"Invalid asset type for scene {expected_id}.")
        previous_start = start
    return assets


def build_render_segments(assets: list[dict], total_duration: float) -> list[dict]:
    """Map semantic scene starts to continuous render intervals.

    Spoken scene timing remains untouched in scene_start/scene_end. Visual cuts
    happen exactly at the next semantic scene start. Any narration pause is
    therefore an explicit hold_after_scene interval owned by the preceding
    scene, rather than being redistributed evenly across unrelated assets.
    """
    if total_duration <= 0:
        raise SystemExit("Narration duration must be positive.")
    if float(assets[-1]["scene_start"]) >= total_duration:
        raise SystemExit("Last scene starts after narration ends.")

    segments: list[dict] = []
    for index, asset in enumerate(assets):
        render_start = 0.0 if index == 0 else float(asset["scene_start"])
        render_end = float(assets[index + 1]["scene_start"]) if index + 1 < len(assets) else total_duration
        scene_start = float(asset["scene_start"])
        scene_end = float(asset["scene_end"])

        if render_end <= render_start:
            raise SystemExit(f"Non-positive render interval for scene {asset['scene_id']}.")
        if scene_start < render_start - TIMING_EPSILON or scene_end > render_end + TIMING_EPSILON:
            raise SystemExit(
                f"Semantic interval {scene_start:.3f}..{scene_end:.3f} does not fit render interval "
                f"{render_start:.3f}..{render_end:.3f} for scene {asset['scene_id']}."
            )

        segments.append({
            "scene_id": int(asset["scene_id"]),
            "asset_id": str(asset["asset_id"]),
            "asset_path": str(asset["path"]),
            "asset_type": str(asset["type"]),
            "provider": str(asset["provider"]),
            "scene_start": scene_start,
            "scene_end": scene_end,
            "render_start": render_start,
            "render_end": render_end,
            "render_duration": render_end - render_start,
            "pre_roll": max(0.0, scene_start - render_start),
            "hold_after_scene": max(0.0, render_end - scene_end),
        })

    if abs(segments[0]["render_start"]) > TIMING_EPSILON:
        raise SystemExit("Rendered timeline does not start at zero.")
    if abs(segments[-1]["render_end"] - total_duration) > TIMING_EPSILON:
        raise SystemExit("Rendered timeline does not end at narration duration.")
    for left, right in zip(segments, segments[1:]):
        if abs(left["render_end"] - right["render_start"]) > TIMING_EPSILON:
            raise SystemExit("Rendered timeline has a gap or overlap.")
    return segments


def build_visuals_segment(segments: list[dict], out_path: Path) -> None:
    inputs: list[str] = []
    filters: list[str] = []

    for index, segment in enumerate(segments):
        path = segment["asset_path"]
        duration = float(segment["render_duration"])
        frames = max(1, round(duration * TARGET_FPS))
        if segment["asset_type"] == "video":
            inputs += ["-stream_loop", "-1", "-i", path]
            filters.append(
                f"[{index}:v]trim=0:{duration:.3f},setpts=PTS-STARTPTS,"
                f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},setsar=1,fps={TARGET_FPS}[v{index}]"
            )
        else:
            inputs += ["-loop", "1", "-i", path]
            filters.append(
                f"[{index}:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},scale={TARGET_WIDTH*2}:{TARGET_HEIGHT*2},"
                f"zoompan=z='min(zoom+0.0015,1.16)':d={frames}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={TARGET_WIDTH}x{TARGET_HEIGHT}:fps={TARGET_FPS},"
                f"setsar=1,trim=0:{duration:.3f},setpts=PTS-STARTPTS[v{index}]"
            )

    concat_inputs = "".join(f"[v{i}]" for i in range(len(segments)))
    filters.append(f"{concat_inputs}concat=n={len(segments)}:v=1:a=0[outv]")
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[outv]", "-an", str(out_path)]
    run(cmd)


def extract_thumbnail(assets: list[dict], out_path: Path) -> bool:
    first_video = next((asset for asset in assets if asset["type"] == "video"), None)
    if not first_video:
        return False
    cmd = [
        "ffmpeg", "-y", "-i", first_video["path"], "-ss", "0.5", "-frames:v", "1",
        "-vf", f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT}",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0 and out_path.exists()


def main() -> None:
    script_path = find_latest("script_[0-9]*.json")
    timestamp = script_path.stem.replace("script_", "")

    voice_path = OUTPUT_DIR / f"voice_{timestamp}.mp3"
    asset_manifest_path = OUTPUT_DIR / f"asset_manifest_{timestamp}.json"
    captions_path = OUTPUT_DIR / f"captions_{timestamp}.srt"
    final_path = OUTPUT_DIR / f"final_{timestamp}.mp4"
    renderer_manifest_path = OUTPUT_DIR / f"renderer_manifest_{timestamp}.json"

    for path in (voice_path, asset_manifest_path, captions_path):
        if not path.exists():
            raise SystemExit(f"Missing {path.name}; M1-M3 must complete before M4 rendering.")

    print("🎬 M4 storyboard-driven rendering...")
    audio_duration = get_audio_duration(voice_path)
    asset_manifest = json.loads(asset_manifest_path.read_text(encoding="utf-8"))
    assets = validate_asset_manifest(asset_manifest)
    segments = build_render_segments(assets, audio_duration)

    print(f"   Narration: {audio_duration:.3f}s; scenes: {len(segments)}")
    for segment in segments:
        print(
            f"   S{segment['scene_id']:02d} render {segment['render_start']:.3f}-{segment['render_end']:.3f}s "
            f"(spoken {segment['scene_start']:.3f}-{segment['scene_end']:.3f}s, "
            f"pause-hold {segment['hold_after_scene']:.3f}s)"
        )

    silent_video_path = OUTPUT_DIR / f"_silent_{timestamp}.mp4"
    build_visuals_segment(segments, silent_video_path)

    renderer_manifest = {
        "schema_version": 1,
        "timestamp": timestamp,
        "strategy": "storyboard_scene_start_cuts_with_previous_scene_pause_hold",
        "target_width": TARGET_WIDTH,
        "target_height": TARGET_HEIGHT,
        "target_fps": TARGET_FPS,
        "audio_duration": audio_duration,
        "scene_count": len(segments),
        "segments": segments,
    }
    renderer_manifest_path.write_text(json.dumps(renderer_manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    thumbnail_path = OUTPUT_DIR / f"thumbnail_{timestamp}.jpg"
    if extract_thumbnail(assets, thumbnail_path):
        print(f"   Thumbnail: {thumbnail_path.name}")

    subs_arg = escape_for_ffmpeg_filter(captions_path)
    music_path = pick_random_music()
    if music_path:
        cmd = [
            "ffmpeg", "-y", "-i", str(silent_video_path), "-i", str(voice_path),
            "-stream_loop", "-1", "-i", str(music_path),
            "-filter_complex",
            f"[0:v]subtitles='{subs_arg}':force_style='{SUBTITLE_STYLE}'[outv];"
            f"[2:a]atrim=0:{audio_duration:.3f},volume={MUSIC_VOLUME}[music];"
            f"[1:a][music]amix=inputs=2:duration=first:dropout_transition=2[outa]",
            "-map", "[outv]", "-map", "[outa]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", str(TARGET_FPS), "-c:a", "aac", "-shortest", str(final_path),
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", str(silent_video_path), "-i", str(voice_path),
            "-filter_complex", f"[0:v]subtitles='{subs_arg}':force_style='{SUBTITLE_STYLE}'[outv]",
            "-map", "[outv]", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", str(TARGET_FPS), "-c:a", "aac", "-shortest", str(final_path),
        ]
    run(cmd)
    silent_video_path.unlink(missing_ok=True)
    print(f"\n✅ M4 render ready: {final_path.name}")
    print(f"✅ Renderer manifest: {renderer_manifest_path.name}")


if __name__ == "__main__":
    main()
