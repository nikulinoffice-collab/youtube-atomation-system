"""M5.4 storyboard renderer; M6.9 narration media is resolved fail-closed."""
import html, json, random, subprocess
from pathlib import Path
from scripts.m6_run_provenance import select_run_artifact, verify_visual_chain, stamp_json_artifact
from urllib.parse import urlparse
from scripts.m6_production_media import ProductionMediaError, resolve_voice_artifact

OUTPUT_DIR=Path(__file__).parent/"output"
MUSIC_DIR=Path(__file__).parent.parent/"assets"/"music"
TARGET_WIDTH=1080; TARGET_HEIGHT=1920; TARGET_FPS=30; MUSIC_VOLUME=.12; TIMING_EPSILON=.050
ALLOWED_MOTIONS={"static","slow_push_in","slow_pull_out","pan_left","pan_right"}
SUBTITLE_STYLE="FontName=Arial,FontSize=16,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=120"

def find_latest(pattern):
    if pattern != "script_[0-9]*.json":
        raise SystemExit(f"Unsupported unbound artifact discovery: {pattern}")
    return select_run_artifact(OUTPUT_DIR, "script_", "script_[0-9]*.json")

def run(cmd):
    r=subprocess.run(cmd,capture_output=True,text=True)
    if r.returncode: print(r.stderr[-4000:]); raise SystemExit(f"Command failed: {' '.join(cmd)}")
def probe_media(path):
    r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=index,codec_type,width,height,r_frame_rate","-of","json",str(path)],capture_output=True,text=True)
    if r.returncode: raise SystemExit(f"ffprobe failed on {path}: {r.stderr}")
    return json.loads(r.stdout)
def get_audio_duration(path): return float(probe_media(path)["format"]["duration"])
def escape_for_ffmpeg_filter(path): return str(path.resolve()).replace("\\","/").replace(":","\\:")
def pick_random_music():
    tracks=list(MUSIC_DIR.glob("*.mp3"))+list(MUSIC_DIR.glob("*.wav")) if MUSIC_DIR.exists() else []
    return random.choice(tracks) if tracks else None
def validate_asset_manifest(manifest):
    assets=manifest.get("assets")
    if not isinstance(assets,list) or not assets or int(manifest.get("scene_count",-1))!=len(assets): raise SystemExit("asset_manifest invalid.")
    prev=-1
    for i,a in enumerate(assets,1):
        start,end=float(a["scene_start"]),float(a["scene_end"]); p=Path(str(a["path"]))
        if int(a.get("scene_id",-1))!=i or start<0 or end<=start or start<=prev: raise SystemExit(f"Invalid scene {i}.")
        if not p.exists() or p.stat().st_size<=0: raise SystemExit(f"Missing/empty scene asset: {p}")
        if a.get("type") not in {"video","image"}: raise SystemExit(f"Invalid asset type for scene {i}.")
        motion=str(a.get("preferred_motion","static"))
        if motion not in ALLOWED_MOTIONS or (a.get("provider")=="source_article" and motion!="static"): raise SystemExit(f"Invalid motion for scene {i}.")
        prev=start
    return [dict(a) for a in assets]
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
            source_url = str(item.get("source_url") or "")
            parsed_url = urlparse(source_url)
            if parsed_url.scheme not in {"https", "http"} or not parsed_url.hostname:
                raise SystemExit("Source article scene requires a valid source_url; refusing stock fallback.")
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


def build_render_segments(assets,total):
    if total<=0 or float(assets[-1]["scene_start"])>=total: raise SystemExit("Invalid narration duration relative to storyboard scenes.")
    out=[]
    for i,a in enumerate(assets):
        rs=0.0 if i==0 else float(a["scene_start"]); re=float(assets[i+1]["scene_start"]) if i+1<len(assets) else total
        ss,se=float(a["scene_start"]),float(a["scene_end"])
        if re<=rs or ss<rs-TIMING_EPSILON or se>re+TIMING_EPSILON: raise SystemExit(f"Invalid render interval scene {i+1}.")
        motion="native_video" if a["type"]=="video" else str(a.get("preferred_motion","static"))
        out.append({"scene_id":int(a["scene_id"]),"asset_id":str(a["asset_id"]),"asset_path":str(a["path"]),"asset_type":str(a["type"]),"provider":str(a["provider"]),"render_transform":str(a.get("render_transform","none")),"preferred_motion":str(a.get("preferred_motion","static")),"resolved_motion":motion,"scene_start":ss,"scene_end":se,"render_start":rs,"render_end":re,"render_duration":re-rs,"pre_roll":max(0,ss-rs),"hold_after_scene":max(0,re-se)})
    return out
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


def extract_thumbnail(assets,out_path): return False

def main():
    script_path=find_latest("script_[0-9]*.json"); timestamp=script_path.stem.replace("script_","")
    try: voice_path=resolve_voice_artifact(OUTPUT_DIR,timestamp)
    except ProductionMediaError as e: raise SystemExit(str(e)) from e
    asset_path=OUTPUT_DIR/f"asset_manifest_{timestamp}.json"; captions=OUTPUT_DIR/f"captions_{timestamp}.srt"; final=OUTPUT_DIR/f"final_{timestamp}.mp4"; renderer=OUTPUT_DIR/f"renderer_manifest_{timestamp}.json"
    for p in (asset_path,captions):
        if not p.exists(): raise SystemExit(f"Missing {p.name}; earlier stages must complete before rendering.")
    verify_visual_chain(OUTPUT_DIR, timestamp)
    renderer.unlink(missing_ok=True)
    duration=get_audio_duration(voice_path); manifest=json.loads(asset_path.read_text()); assets=prepare_render_assets(validate_asset_manifest(manifest),json.loads(script_path.read_text()),timestamp); segments=build_render_segments(assets,duration)
    silent=OUTPUT_DIR/f"_silent_{timestamp}.mp4"; build_visuals_segment(segments,silent)
    renderer_payload = {"schema_version":2,"milestone":"M5.4","timestamp":timestamp,"strategy":"storyboard_scene_start_cuts_with_previous_scene_pause_hold","source_card_strategy":"concise_caption_safe_mobile_card","motion_policy":{"allowed_still_motions":sorted(ALLOWED_MOTIONS),"video_policy":"preserve_native_motion","source_card_policy":"static_for_readability"},"target_width":TARGET_WIDTH,"target_height":TARGET_HEIGHT,"target_fps":TARGET_FPS,"audio_duration":duration,"scene_count":len(segments),"segments":segments}
    subs=escape_for_ffmpeg_filter(captions); cmd=["ffmpeg","-y","-i",str(silent),"-i",str(voice_path),"-filter_complex",f"[0:v]subtitles='{subs}':force_style='{SUBTITLE_STYLE}'[outv]","-map","[outv]","-map","1:a","-c:v","libx264","-pix_fmt","yuv420p","-r",str(TARGET_FPS),"-c:a","aac","-shortest",str(final)]
    run(cmd)
    renderer_payload = stamp_json_artifact(renderer_payload, "pre-m7.renderer.v1",
                                          "agents.video_agent", timestamp,
                                          (asset_path, voice_path, captions, final))
    renderer.write_text(json.dumps(renderer_payload, indent=2), encoding="utf-8")
    silent.unlink(missing_ok=True); print(f"✅ M5.4 render ready: {final.name}")
if __name__=="__main__": main()
