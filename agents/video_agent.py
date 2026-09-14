"""M4 Storyboard-driven video renderer.

Consumes asset_manifest_<timestamp>.json as the canonical visual timeline.
Visual cuts occur at storyboard scene starts rather than by equal division.
Narration pauses explicitly hold the preceding scene visual until the next
semantic scene begins. Source-article screenshots are rendered as readable
mobile source cards at render time while retaining original provenance.
"""

import html
import json
import random
import subprocess
from pathlib import Path
from urllib.parse import urlparse

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
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=index,codec_type,width,height,r_frame_rate", "-of", "json", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"ffprobe failed on {path}: {result.stderr}")
    return json.loads(result.stdout)


def get_audio_duration(audio_path: Path) -> float:
    return float(probe_media(audio_path)["format"]["duration"])


def escape_for_ffmpeg_filter(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", "\\:")


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
        start, end = float(asset["scene_start"]), float(asset["scene_end"])
        if start < 0 or end <= start or start <= previous_start:
            raise SystemExit(f"Invalid scene timing for scene {expected_id}: {start}..{end}")
        path = Path(str(asset["path"]))
        if not path.exists() or path.stat().st_size <= 0:
            raise SystemExit(f"Missing/empty scene asset: {path}")
        if asset.get("type") not in {"video", "image"}:
            raise SystemExit(f"Invalid asset type for scene {expected_id}.")
        previous_start = start
    return [dict(asset) for asset in assets]


def render_source_card(script: dict, asset: dict, timestamp: str) -> Path:
    """Create a legible 1080x1920 source card instead of a full-page screenshot."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("Playwright is required for source-card rendering.") from exc

    headline = html.escape(str(script.get("source_title") or script.get("title") or "Source article"))
    source_url = str(asset.get("source_url", ""))
    domain = html.escape(urlparse(source_url).netloc.removeprefix("www.") or "SOURCE")
    output_path = OUTPUT_DIR / f"source_card_{timestamp}_scene_{int(asset['scene_id']):02d}.jpg"
    document = f"""<!doctype html><html><head><style>
      *{{box-sizing:border-box}} body{{margin:0;width:1080px;height:1920px;background:#0d0f14;color:white;
      font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;padding:90px}}
      .card{{width:900px;min-height:760px;background:#171b23;border:2px solid #394150;border-radius:42px;
      padding:72px;display:flex;flex-direction:column;justify-content:center;box-shadow:0 20px 80px #0008}}
      .label{{font-size:34px;letter-spacing:5px;color:#9ba7ba;font-weight:700;margin-bottom:42px}}
      .headline{{font-size:68px;line-height:1.08;font-weight:800;margin-bottom:54px}}
      .domain{{font-size:38px;color:#c9d3e2;font-weight:700}}
      .note{{font-size:26px;color:#7f8a9d;margin-top:18px}}
    </style></head><body><div class="card"><div class="label">SOURCE</div>
    <div class="headline">{headline}</div><div class="domain">{domain}</div>
    <div class="note">Referenced in this story</div></div></body></html>"""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": TARGET_WIDTH, "height": TARGET_HEIGHT})
        page.set_content(document, wait_until="load")
        page.screenshot(path=str(output_path), type="jpeg", quality=92)
        browser.close()
    if not output_path.exists() or output_path.stat().st_size <= 0:
        raise SystemExit("Source-card rendering produced no image.")
    return output_path


def prepare_render_assets(assets: list[dict], script: dict, timestamp: str) -> list[dict]:
    prepared: list[dict] = []
    for asset in assets:
        item = dict(asset)
        if item.get("provider") == "source_article":
            card_path = render_source_card(script, item, timestamp)
            item["original_asset_path"] = item["path"]
            item["path"] = str(card_path)
            item["render_transform"] = "readable_source_card"
            item["type"] = "image"
        else:
            item["render_transform"] = "none"
        prepared.append(item)
    return prepared


def build_render_segments(assets: list[dict], total_duration: float) -> list[dict]:
    if total_duration <= 0 or float(assets[-1]["scene_start"]) >= total_duration:
        raise SystemExit("Invalid narration duration relative to storyboard scenes.")
    segments: list[dict] = []
    for index, asset in enumerate(assets):
        render_start = 0.0 if index == 0 else float(asset["scene_start"])
        render_end = float(assets[index + 1]["scene_start"]) if index + 1 < len(assets) else total_duration
        scene_start, scene_end = float(asset["scene_start"]), float(asset["scene_end"])
        if render_end <= render_start:
            raise SystemExit(f"Non-positive render interval for scene {asset['scene_id']}.")
        if scene_start < render_start - TIMING_EPSILON or scene_end > render_end + TIMING_EPSILON:
            raise SystemExit(f"Semantic interval does not fit render interval for scene {asset['scene_id']}.")
        segments.append({
            "scene_id": int(asset["scene_id"]), "asset_id": str(asset["asset_id"]),
            "asset_path": str(asset["path"]), "asset_type": str(asset["type"]),
            "provider": str(asset["provider"]), "render_transform": str(asset.get("render_transform", "none")),
            "scene_start": scene_start, "scene_end": scene_end,
            "render_start": render_start, "render_end": render_end,
            "render_duration": render_end - render_start,
            "pre_roll": max(0.0, scene_start - render_start),
            "hold_after_scene": max(0.0, render_end - scene_end),
        })
    if abs(segments[0]["render_start"]) > TIMING_EPSILON or abs(segments[-1]["render_end"] - total_duration) > TIMING_EPSILON:
        raise SystemExit("Rendered timeline does not cover narration duration.")
    for left, right in zip(segments, segments[1:]):
        if abs(left["render_end"] - right["render_start"]) > TIMING_EPSILON:
            raise SystemExit("Rendered timeline has a gap or overlap.")
    return segments


def build_visuals_segment(segments: list[dict], out_path: Path) -> None:
    inputs, filters = [], []
    for index, segment in enumerate(segments):
        path, duration = segment["asset_path"], float(segment["render_duration"])
        frames = max(1, round(duration * TARGET_FPS))
        if segment["asset_type"] == "video":
            inputs += ["-stream_loop", "-1", "-i", path]
            filters.append(f"[{index}:v]trim=0:{duration:.3f},setpts=PTS-STARTPTS,scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT},setsar=1,fps={TARGET_FPS}[v{index}]")
        else:
            inputs += ["-loop", "1", "-i", path]
            filters.append(f"[{index}:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT},scale={TARGET_WIDTH*2}:{TARGET_HEIGHT*2},zoompan=z='min(zoom+0.0015,1.16)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={TARGET_WIDTH}x{TARGET_HEIGHT}:fps={TARGET_FPS},setsar=1,trim=0:{duration:.3f},setpts=PTS-STARTPTS[v{index}]")
    filters.append("".join(f"[v{i}]" for i in range(len(segments))) + f"concat=n={len(segments)}:v=1:a=0[outv]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[outv]", "-an", str(out_path)])


def extract_thumbnail(assets: list[dict], out_path: Path) -> bool:
    first_video = next((asset for asset in assets if asset["type"] == "video"), None)
    if not first_video:
        return False
    result = subprocess.run(["ffmpeg", "-y", "-i", first_video["path"], "-ss", "0.5", "-frames:v", "1", "-vf", f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT}", str(out_path)], capture_output=True, text=True)
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

    script = json.loads(script_path.read_text(encoding="utf-8"))
    audio_duration = get_audio_duration(voice_path)
    manifest = json.loads(asset_manifest_path.read_text(encoding="utf-8"))
    original_assets = validate_asset_manifest(manifest)
    assets = prepare_render_assets(original_assets, script, timestamp)
    segments = build_render_segments(assets, audio_duration)
    print(f"🎬 M4 storyboard-driven rendering: {len(segments)} scenes, narration={audio_duration:.3f}s")
    for segment in segments:
        print(f"   S{segment['scene_id']:02d} {segment['render_start']:.3f}-{segment['render_end']:.3f}s spoken={segment['scene_start']:.3f}-{segment['scene_end']:.3f}s hold={segment['hold_after_scene']:.3f}s transform={segment['render_transform']}")

    silent_path = OUTPUT_DIR / f"_silent_{timestamp}.mp4"
    build_visuals_segment(segments, silent_path)
    renderer_manifest_path.write_text(json.dumps({
        "schema_version": 1, "timestamp": timestamp,
        "strategy": "storyboard_scene_start_cuts_with_previous_scene_pause_hold",
        "source_card_strategy": "readable_mobile_card",
        "target_width": TARGET_WIDTH, "target_height": TARGET_HEIGHT, "target_fps": TARGET_FPS,
        "audio_duration": audio_duration, "scene_count": len(segments), "segments": segments,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    thumbnail_path = OUTPUT_DIR / f"thumbnail_{timestamp}.jpg"
    extract_thumbnail(original_assets, thumbnail_path)
    subs_arg = escape_for_ffmpeg_filter(captions_path)
    music_path = pick_random_music()
    if music_path:
        cmd = ["ffmpeg", "-y", "-i", str(silent_path), "-i", str(voice_path), "-stream_loop", "-1", "-i", str(music_path), "-filter_complex", f"[0:v]subtitles='{subs_arg}':force_style='{SUBTITLE_STYLE}'[outv];[2:a]atrim=0:{audio_duration:.3f},volume={MUSIC_VOLUME}[music];[1:a][music]amix=inputs=2:duration=first:dropout_transition=2[outa]", "-map", "[outv]", "-map", "[outa]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(TARGET_FPS), "-c:a", "aac", "-shortest", str(final_path)]
    else:
        cmd = ["ffmpeg", "-y", "-i", str(silent_path), "-i", str(voice_path), "-filter_complex", f"[0:v]subtitles='{subs_arg}':force_style='{SUBTITLE_STYLE}'[outv]", "-map", "[outv]", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(TARGET_FPS), "-c:a", "aac", "-shortest", str(final_path)]
    run(cmd)
    silent_path.unlink(missing_ok=True)
    print(f"✅ M4 render ready: {final_path.name}")
    print(f"✅ Renderer manifest: {renderer_manifest_path.name}")


if __name__ == "__main__":
    main()
