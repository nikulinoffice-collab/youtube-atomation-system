"""M5.4 storyboard-driven renderer with controlled motion and mobile source cards.

Consumes asset_manifest_<timestamp>.json as the canonical visual timeline.
Visual cuts occur at storyboard scene starts rather than by equal division.
Narration pauses explicitly hold the preceding scene visual until the next
semantic scene begins. Still-image motion follows the M5 visual-direction
contract; video assets retain their native motion. Source-article screenshots
are replaced at render time with concise caption-safe mobile source cards while
retaining the original provenance in the renderer manifest.
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
ALLOWED_MOTIONS = {"static", "slow_push_in", "slow_pull_out", "pan_left", "pan_right"}
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
        motion = str(asset.get("preferred_motion", "static"))
        if motion not in ALLOWED_MOTIONS:
            raise SystemExit(f"Invalid preferred_motion for scene {expected_id}: {motion!r}")
        if asset.get("provider") == "source_article" and motion != "static":
            raise SystemExit(f"Source-card scene {expected_id} must use static motion for readability.")
        previous_start = start
    return [dict(asset) for asset in assets]


def compact_headline(text: str, limit: int = 116) -> str:
    clean = " ".join(str(text).split())
    if len(clean) <= limit:
        return clean
    shortened = clean[: limit + 1].rsplit(" ", 1)[0].rstrip(" ,.;:-")
    return f"{shortened}…"


def source_publisher(source_url: str) -> tuple[str, str]:
    domain = urlparse(source_url).netloc.removeprefix("www.") or "source"
    publisher = domain.split(".")[0].replace("-", " ").strip().upper() or "SOURCE"
    return publisher, domain


def render_source_card(script: dict, asset: dict, timestamp: str) -> Path:
    """Create a concise source card that leaves the subtitle-safe lower region clear."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("Playwright is required for source-card rendering.") from exc

    raw_headline = str(script.get("source_title") or script.get("title") or "Source article")
    headline = html.escape(compact_headline(raw_headline))
    source_url = str(asset.get("source_url", ""))
    publisher_raw, domain_raw = source_publisher(source_url)
    publisher = html.escape(publisher_raw)
    domain = html.escape(domain_raw)
    source_date_raw = str(script.get("source_date") or script.get("published_at") or "").strip()
    source_date = html.escape(source_date_raw[:32])
    output_path = OUTPUT_DIR / f"source_card_{timestamp}_scene_{int(asset['scene_id']):02d}.jpg"
    date_html = f'<div class="date">{source_date}</div>' if source_date else ""
    document = f"""<!doctype html><html><head><style>
      *{{box-sizing:border-box}}
      body{{margin:0;width:1080px;height:1920px;background:#0b0e13;color:white;font-family:Arial,sans-serif;
      padding:150px 84px 0 84px;overflow:hidden}}
      .card{{width:912px;max-height:1030px;background:#171c25;border:2px solid #3b4658;border-radius:40px;
      padding:64px 64px 58px 64px;box-shadow:0 24px 90px #0009;overflow:hidden}}
      .publisher{{font-size:34px;line-height:1;font-weight:800;letter-spacing:4px;color:#dce5f2;margin-bottom:40px}}
      .headline{{font-size:58px;line-height:1.10;font-weight:800;display:-webkit-box;-webkit-line-clamp:7;
      -webkit-box-orient:vertical;overflow:hidden;margin-bottom:44px}}
      .meta{{border-top:2px solid #343d4b;padding-top:32px}}
      .domain{{font-size:34px;line-height:1.2;color:#c6d2e2;font-weight:700}}
      .date{{font-size:27px;line-height:1.2;color:#8694a8;margin-top:14px}}
      .source-label{{font-size:25px;color:#718096;letter-spacing:3px;margin-top:24px}}
      .caption-safe{{position:absolute;left:0;right:0;bottom:0;height:520px;border-top:1px solid #ffffff10}}
    </style></head><body><div class="card"><div class="publisher">{publisher}</div>
    <div class="headline">{headline}</div><div class="meta"><div class="domain">{domain}</div>{date_html}
    <div class="source-label">SOURCE</div></div></div><div class="caption-safe"></div></body></html>"""
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
            item["render_transform"] = "concise_caption_safe_source_card"
            item["type"] = "image"
            item["preferred_motion"] = "static"
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
        preferred_motion = str(asset.get("preferred_motion", "static"))
        resolved_motion = "native_video" if asset["type"] == "video" else preferred_motion
        segments.append({
            "scene_id": int(asset["scene_id"]), "asset_id": str(asset["asset_id"]),
            "asset_path": str(asset["path"]), "asset_type": str(asset["type"]),
            "provider": str(asset["provider"]), "render_transform": str(asset.get("render_transform", "none")),
            "preferred_motion": preferred_motion, "resolved_motion": resolved_motion,
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


def still_motion_filter(index: int, duration: float, frames: int, motion: str) -> str:
    prefix = f"[{index}:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT},scale={TARGET_WIDTH*2}:{TARGET_HEIGHT*2},"
    center = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if motion == "static":
        return f"[{index}:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT},setsar=1,fps={TARGET_FPS},trim=0:{duration:.3f},setpts=PTS-STARTPTS[v{index}]"
    if motion == "slow_push_in":
        zoom = "z='min(zoom+0.0013,1.12)'"
        position = center
    elif motion == "slow_pull_out":
        zoom = "z='if(eq(on,0),1.12,max(1.0,zoom-0.0013))'"
        position = center
    elif motion == "pan_left":
        zoom = "z='1.08'"
        denom = max(1, frames - 1)
        position = f"x='(iw-iw/zoom)*(1-on/{denom})':y='ih/2-(ih/zoom/2)'"
    elif motion == "pan_right":
        zoom = "z='1.08'"
        denom = max(1, frames - 1)
        position = f"x='(iw-iw/zoom)*(on/{denom})':y='ih/2-(ih/zoom/2)'"
    else:
        raise SystemExit(f"Unsupported still motion: {motion}")
    return f"{prefix}zoompan={zoom}:d={frames}:{position}:s={TARGET_WIDTH}x{TARGET_HEIGHT}:fps={TARGET_FPS},setsar=1,trim=0:{duration:.3f},setpts=PTS-STARTPTS[v{index}]"


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
            filters.append(still_motion_filter(index, duration, frames, str(segment["resolved_motion"])))
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
            raise SystemExit(f"Missing {path.name}; M1-M3 must complete before M5.4 rendering.")

    script = json.loads(script_path.read_text(encoding="utf-8"))
    audio_duration = get_audio_duration(voice_path)
    manifest = json.loads(asset_manifest_path.read_text(encoding="utf-8"))
    original_assets = validate_asset_manifest(manifest)
    assets = prepare_render_assets(original_assets, script, timestamp)
    segments = build_render_segments(assets, audio_duration)
    print(f"🎬 M5.4 storyboard rendering: {len(segments)} scenes, narration={audio_duration:.3f}s")
    for segment in segments:
        print(f"   S{segment['scene_id']:02d} {segment['render_start']:.3f}-{segment['render_end']:.3f}s spoken={segment['scene_start']:.3f}-{segment['scene_end']:.3f}s motion={segment['resolved_motion']} hold={segment['hold_after_scene']:.3f}s transform={segment['render_transform']}")

    silent_path = OUTPUT_DIR / f"_silent_{timestamp}.mp4"
    build_visuals_segment(segments, silent_path)
    renderer_manifest_path.write_text(json.dumps({
        "schema_version": 2, "milestone": "M5.4", "timestamp": timestamp,
        "strategy": "storyboard_scene_start_cuts_with_previous_scene_pause_hold",
        "source_card_strategy": "concise_caption_safe_mobile_card",
        "motion_policy": {
            "allowed_still_motions": sorted(ALLOWED_MOTIONS),
            "video_policy": "preserve_native_motion",
            "source_card_policy": "static_for_readability",
        },
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
    print(f"✅ M5.4 render ready: {final_path.name}")
    print(f"✅ Renderer manifest: {renderer_manifest_path.name}")


if __name__ == "__main__":
    main()
