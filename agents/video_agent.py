"""M5.4 storyboard renderer; M6.9 narration media is resolved fail-closed."""
import html, json, random, subprocess
from pathlib import Path
from urllib.parse import urlparse
from scripts.m6_production_media import ProductionMediaError, resolve_voice_artifact

OUTPUT_DIR=Path(__file__).parent/"output"
MUSIC_DIR=Path(__file__).parent.parent/"assets"/"music"
TARGET_WIDTH=1080; TARGET_HEIGHT=1920; TARGET_FPS=30; MUSIC_VOLUME=.12; TIMING_EPSILON=.050
ALLOWED_MOTIONS={"static","slow_push_in","slow_pull_out","pan_left","pan_right"}
SUBTITLE_STYLE="FontName=Arial,FontSize=16,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=120"

def find_latest(pattern):
    m=sorted(OUTPUT_DIR.glob(pattern))
    if not m: raise SystemExit(f"No files matching {pattern} in agents/output/. Run earlier steps first.")
    return m[-1]
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
def prepare_render_assets(assets,script,timestamp): return [dict(a,render_transform="none") for a in assets]
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
def build_visuals_segment(segments,out_path):
    inputs=[]; filters=[]
    for i,s in enumerate(segments):
        d=float(s["render_duration"]); p=s["asset_path"]
        if s["asset_type"]=="video": inputs += ["-stream_loop","-1","-i",p]
        else: inputs += ["-loop","1","-i",p]
        filters.append(f"[{i}:v]trim=0:{d:.3f},setpts=PTS-STARTPTS,scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT},setsar=1,fps={TARGET_FPS}[v{i}]")
    filters.append("".join(f"[v{i}]" for i in range(len(segments)))+f"concat=n={len(segments)}:v=1:a=0[outv]")
    run(["ffmpeg","-y",*inputs,"-filter_complex",";".join(filters),"-map","[outv]","-an",str(out_path)])
def extract_thumbnail(assets,out_path): return False

def main():
    script_path=find_latest("script_[0-9]*.json"); timestamp=script_path.stem.replace("script_","")
    try: voice_path=resolve_voice_artifact(OUTPUT_DIR,timestamp)
    except ProductionMediaError as e: raise SystemExit(str(e)) from e
    asset_path=OUTPUT_DIR/f"asset_manifest_{timestamp}.json"; captions=OUTPUT_DIR/f"captions_{timestamp}.srt"; final=OUTPUT_DIR/f"final_{timestamp}.mp4"; renderer=OUTPUT_DIR/f"renderer_manifest_{timestamp}.json"
    for p in (asset_path,captions):
        if not p.exists(): raise SystemExit(f"Missing {p.name}; earlier stages must complete before rendering.")
    duration=get_audio_duration(voice_path); manifest=json.loads(asset_path.read_text()); assets=prepare_render_assets(validate_asset_manifest(manifest),json.loads(script_path.read_text()),timestamp); segments=build_render_segments(assets,duration)
    silent=OUTPUT_DIR/f"_silent_{timestamp}.mp4"; build_visuals_segment(segments,silent)
    renderer.write_text(json.dumps({"schema_version":2,"milestone":"M5.4","timestamp":timestamp,"strategy":"storyboard_scene_start_cuts_with_previous_scene_pause_hold","target_width":TARGET_WIDTH,"target_height":TARGET_HEIGHT,"target_fps":TARGET_FPS,"audio_duration":duration,"scene_count":len(segments),"segments":segments},indent=2),encoding="utf-8")
    subs=escape_for_ffmpeg_filter(captions); cmd=["ffmpeg","-y","-i",str(silent),"-i",str(voice_path),"-filter_complex",f"[0:v]subtitles='{subs}':force_style='{SUBTITLE_STYLE}'[outv]","-map","[outv]","-map","1:a","-c:v","libx264","-pix_fmt","yuv420p","-r",str(TARGET_FPS),"-c:a","aac","-shortest",str(final)]
    run(cmd); silent.unlink(missing_ok=True); print(f"✅ M5.4 render ready: {final.name}")
if __name__=="__main__": main()
