"""M3 Semantic Visuals Agent.

Consumes storyboard_<timestamp>.json and acquires exactly one visual asset per
storyboard scene. Query order is deterministic: storyboard queries are tried in
order, followed by conservative generic fallbacks. Provider provenance is
recorded in asset_manifest_<timestamp>.json. A compatibility visuals_<timestamp>.json
is also written for the pre-M4 renderer; asset_manifest is the canonical M3 output.
"""

import json
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("PEXELS_API_KEY")
OUTPUT_DIR = Path(__file__).parent / "output"
STATE_DIR = Path(__file__).parent / "state"
USED_VISUALS_FILE = STATE_DIR / "used_visuals.json"

VIDEO_SEARCH_URL = "https://api.pexels.com/videos/search"
PHOTO_SEARCH_URL = "https://api.pexels.com/v1/search"
GENERIC_FALLBACKS = ["technology", "computer", "digital network"]
SEARCH_PAGES = [1, 2]
PER_PAGE = 8


class AssetAcquisitionError(RuntimeError):
    pass


def find_latest_storyboard() -> Path:
    files = sorted(OUTPUT_DIR.glob("storyboard_[0-9]*.json"))
    if not files:
        raise SystemExit("No storyboard_<timestamp>.json found. Run storyboard_agent.py first.")
    return files[-1]


def load_used_ids(limit: int = 500) -> set[str]:
    if not USED_VISUALS_FILE.exists():
        return set()
    try:
        data = json.loads(USED_VISUALS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return set()
        return {str(item) for item in data[-limit:]}
    except (json.JSONDecodeError, OSError):
        return set()


def save_used_ids(new_ids: list[str], limit: int = 500) -> None:
    existing = list(load_used_ids(limit=10_000))
    seen = set(existing)
    for item in new_ids:
        if item not in seen:
            existing.append(item)
            seen.add(item)
    STATE_DIR.mkdir(exist_ok=True)
    USED_VISUALS_FILE.write_text(json.dumps(existing[-limit:], indent=2), encoding="utf-8")


def download_file(url: str, dest: Path) -> None:
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 16):
                if chunk:
                    handle.write(chunk)
    if not dest.exists() or dest.stat().st_size == 0:
        raise AssetAcquisitionError(f"Downloaded empty asset: {dest}")


def request_json(url: str, params: dict[str, Any]) -> dict:
    response = requests.get(
        url,
        headers={"Authorization": API_KEY},
        params=params,
        timeout=25,
    )
    if response.status_code == 401:
        raise SystemExit("Pexels rejected PEXELS_API_KEY.")
    if response.status_code == 429:
        raise AssetAcquisitionError("Pexels rate limit reached (HTTP 429).")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise AssetAcquisitionError("Pexels returned a non-object response.")
    return payload


def search_videos(query: str, page: int) -> list[dict]:
    payload = request_json(
        VIDEO_SEARCH_URL,
        {
            "query": query,
            "orientation": "portrait",
            "size": "medium",
            "per_page": PER_PAGE,
            "page": page,
        },
    )
    videos = payload.get("videos", [])
    return videos if isinstance(videos, list) else []


def search_photos(query: str, page: int) -> list[dict]:
    payload = request_json(
        PHOTO_SEARCH_URL,
        {
            "query": query,
            "orientation": "portrait",
            "size": "large",
            "per_page": PER_PAGE,
            "page": page,
        },
    )
    photos = payload.get("photos", [])
    return photos if isinstance(photos, list) else []


def best_video_file(video: dict) -> dict | None:
    candidates = [
        item for item in video.get("video_files", [])
        if item.get("file_type") == "video/mp4"
        and int(item.get("width") or 0) > 0
        and int(item.get("height") or 0) > int(item.get("width") or 0)
        and item.get("link")
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda item: (abs(int(item.get("width") or 0) - 720), -int(item.get("height") or 0)))
    return candidates[0]


def query_candidates(scene: dict) -> list[str]:
    raw = scene.get("search_queries")
    if not isinstance(raw, list):
        raise AssetAcquisitionError(f"Scene {scene.get('scene_id')} has no valid search_queries array.")
    candidates: list[str] = []
    seen: set[str] = set()
    for value in [*raw, *GENERIC_FALLBACKS]:
        query = str(value).strip()
        key = query.casefold()
        if len(query) >= 3 and key not in seen:
            seen.add(key)
            candidates.append(query)
    if not candidates:
        raise AssetAcquisitionError(f"Scene {scene.get('scene_id')} has no usable search query.")
    return candidates


def capture_source_screenshot(url: str, out_path: Path) -> bool:
    if not url:
        return False
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page.goto(url, timeout=25_000, wait_until="domcontentloaded")
            for selector in ["text=Accept", "text=I Agree", "text=Accept All"]:
                try:
                    page.click(selector, timeout=1000)
                    break
                except Exception:
                    pass
            page.wait_for_timeout(900)
            page.screenshot(path=str(out_path))
            browser.close()
        return out_path.exists() and out_path.stat().st_size > 0
    except Exception as exc:
        print(f"   source screenshot unavailable: {exc}")
        return False


def source_link_for_timestamp(timestamp: str) -> str:
    path = OUTPUT_DIR / f"script_{timestamp}.json"
    if not path.exists():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return str(data.get("source_link", "")).strip()
    except (json.JSONDecodeError, OSError):
        return ""


def video_entry(scene: dict, video: dict, file_info: dict, query: str, page: int, path: Path) -> dict:
    return {
        "scene_id": int(scene["scene_id"]),
        "scene_start": float(scene["start"]),
        "scene_end": float(scene["end"]),
        "required_duration": float(scene["duration"]),
        "visual_intent": str(scene["visual_intent"]),
        "preferred_asset_type": str(scene.get("preferred_asset_type", "either")),
        "path": str(path),
        "type": "video",
        "provider": "pexels",
        "asset_id": str(video["id"]),
        "query": query,
        "query_page": page,
        "source_url": str(video.get("url", "")),
        "creator": str(video.get("user", {}).get("name", "")),
        "creator_url": str(video.get("user", {}).get("url", "")),
        "provider_duration": video.get("duration"),
        "download_width": file_info.get("width"),
        "download_height": file_info.get("height"),
    }


def photo_entry(scene: dict, photo: dict, query: str, page: int, path: Path) -> dict:
    return {
        "scene_id": int(scene["scene_id"]),
        "scene_start": float(scene["start"]),
        "scene_end": float(scene["end"]),
        "required_duration": float(scene["duration"]),
        "visual_intent": str(scene["visual_intent"]),
        "preferred_asset_type": str(scene.get("preferred_asset_type", "either")),
        "path": str(path),
        "type": "image",
        "provider": "pexels",
        "asset_id": f"photo_{photo['id']}",
        "query": query,
        "query_page": page,
        "source_url": str(photo.get("url", "")),
        "creator": str(photo.get("photographer", "")),
        "creator_url": str(photo.get("photographer_url", "")),
        "provider_duration": None,
        "download_width": photo.get("width"),
        "download_height": photo.get("height"),
    }


def source_entry(scene: dict, source_url: str, path: Path) -> dict:
    return {
        "scene_id": int(scene["scene_id"]),
        "scene_start": float(scene["start"]),
        "scene_end": float(scene["end"]),
        "required_duration": float(scene["duration"]),
        "visual_intent": str(scene["visual_intent"]),
        "preferred_asset_type": str(scene.get("preferred_asset_type", "source_card")),
        "path": str(path),
        "type": "image",
        "provider": "source_article",
        "asset_id": f"source_scene_{scene['scene_id']}",
        "query": "source_article",
        "query_page": None,
        "source_url": source_url,
        "creator": "",
        "creator_url": "",
        "provider_duration": None,
        "download_width": 1080,
        "download_height": 1920,
    }


def try_video(scene: dict, timestamp: str, used: set[str], reserved: set[str]) -> dict | None:
    for query in query_candidates(scene):
        for page in SEARCH_PAGES:
            try:
                results = search_videos(query, page)
            except (requests.RequestException, AssetAcquisitionError) as exc:
                print(f"   video search failed scene={scene['scene_id']} query={query!r}: {exc}")
                continue
            for video in results:
                asset_id = str(video.get("id", ""))
                if not asset_id or asset_id in used or asset_id in reserved:
                    continue
                file_info = best_video_file(video)
                if not file_info:
                    continue
                path = OUTPUT_DIR / f"visual_{timestamp}_scene_{int(scene['scene_id']):02d}.mp4"
                try:
                    download_file(str(file_info["link"]), path)
                except (requests.RequestException, AssetAcquisitionError) as exc:
                    print(f"   video download failed id={asset_id}: {exc}")
                    path.unlink(missing_ok=True)
                    continue
                reserved.add(asset_id)
                return video_entry(scene, video, file_info, query, page, path)
    return None


def try_photo(scene: dict, timestamp: str, used: set[str], reserved: set[str]) -> dict | None:
    for query in query_candidates(scene):
        for page in SEARCH_PAGES:
            try:
                results = search_photos(query, page)
            except (requests.RequestException, AssetAcquisitionError) as exc:
                print(f"   photo search failed scene={scene['scene_id']} query={query!r}: {exc}")
                continue
            for photo in results:
                numeric_id = str(photo.get("id", ""))
                asset_id = f"photo_{numeric_id}" if numeric_id else ""
                if not asset_id or asset_id in used or asset_id in reserved:
                    continue
                src = photo.get("src", {})
                url = src.get("large2x") or src.get("large") or src.get("portrait")
                if not url:
                    continue
                path = OUTPUT_DIR / f"visual_{timestamp}_scene_{int(scene['scene_id']):02d}.jpg"
                try:
                    download_file(str(url), path)
                except (requests.RequestException, AssetAcquisitionError) as exc:
                    print(f"   photo download failed id={asset_id}: {exc}")
                    path.unlink(missing_ok=True)
                    continue
                reserved.add(asset_id)
                return photo_entry(scene, photo, query, page, path)
    return None


def acquire_scene(scene: dict, timestamp: str, source_url: str, used: set[str], reserved: set[str]) -> dict:
    preferred = str(scene.get("preferred_asset_type", "either"))
    if preferred == "source_card" and source_url:
        path = OUTPUT_DIR / f"visual_{timestamp}_scene_{int(scene['scene_id']):02d}_source.jpg"
        print(f"   scene {scene['scene_id']}: source article")
        if capture_source_screenshot(source_url, path):
            return source_entry(scene, source_url, path)
        path.unlink(missing_ok=True)

    order = ["video", "image"]
    if preferred == "image":
        order = ["image", "video"]
    elif preferred in {"video", "either", "source_card"}:
        order = ["video", "image"]

    for kind in order:
        print(f"   scene {scene['scene_id']}: trying {kind} for {scene['visual_intent']!r}")
        entry = try_video(scene, timestamp, used, reserved) if kind == "video" else try_photo(scene, timestamp, used, reserved)
        if entry:
            return entry
    raise AssetAcquisitionError(
        f"Scene {scene['scene_id']} failed closed: no usable asset for queries {query_candidates(scene)!r}."
    )


def validate_manifest(manifest: dict, storyboard: dict) -> None:
    scenes = storyboard.get("scenes")
    assets = manifest.get("assets")
    if not isinstance(scenes, list) or not scenes:
        raise AssetAcquisitionError("Storyboard has no scenes.")
    if not isinstance(assets, list) or len(assets) != len(scenes):
        raise AssetAcquisitionError("Asset manifest must contain exactly one asset per storyboard scene.")
    if manifest.get("scene_count") != len(scenes):
        raise AssetAcquisitionError("Asset manifest scene_count mismatch.")

    seen_ids: set[str] = set()
    for scene, asset in zip(scenes, assets):
        if int(asset.get("scene_id", -1)) != int(scene["scene_id"]):
            raise AssetAcquisitionError("Asset manifest scene order/id mismatch.")
        if abs(float(asset["scene_start"]) - float(scene["start"])) > 1e-6:
            raise AssetAcquisitionError(f"Scene {scene['scene_id']} start mismatch.")
        if abs(float(asset["scene_end"]) - float(scene["end"])) > 1e-6:
            raise AssetAcquisitionError(f"Scene {scene['scene_id']} end mismatch.")
        path = Path(str(asset.get("path", "")))
        if not path.exists() or path.stat().st_size <= 0:
            raise AssetAcquisitionError(f"Scene {scene['scene_id']} asset file missing/empty: {path}")
        if asset.get("type") not in {"video", "image"}:
            raise AssetAcquisitionError(f"Scene {scene['scene_id']} has invalid asset type.")
        if asset.get("provider") not in {"pexels", "source_article"}:
            raise AssetAcquisitionError(f"Scene {scene['scene_id']} has invalid provider.")
        if not str(asset.get("source_url", "")).strip():
            raise AssetAcquisitionError(f"Scene {scene['scene_id']} has no provenance source_url.")
        asset_id = str(asset.get("asset_id", ""))
        if not asset_id or asset_id in seen_ids:
            raise AssetAcquisitionError(f"Scene {scene['scene_id']} has missing/duplicate asset_id {asset_id!r}.")
        seen_ids.add(asset_id)


def legacy_visuals(assets: list[dict]) -> list[dict]:
    """Compatibility view for the current equal-duration pre-M4 renderer."""
    return [
        {
            "path": asset["path"],
            "type": asset["type"],
            "search_term": asset["query"],
            "pexels_id": asset["asset_id"] if asset["provider"] == "pexels" else None,
            "duration_seconds": asset.get("provider_duration"),
            "scene_id": asset["scene_id"],
        }
        for asset in assets
    ]


def main() -> None:
    if not API_KEY:
        raise SystemExit("PEXELS_API_KEY is not set.")

    storyboard_path = find_latest_storyboard()
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    scenes = storyboard.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise SystemExit("Storyboard contains no scenes.")
    timestamp = storyboard_path.stem.replace("storyboard_", "")
    source_url = source_link_for_timestamp(timestamp)

    used = load_used_ids()
    reserved: set[str] = set()
    assets: list[dict] = []
    print(f"🎞️ M3 semantic acquisition: {len(scenes)} storyboard scenes")
    for scene in scenes:
        try:
            asset = acquire_scene(scene, timestamp, source_url, used, reserved)
        except AssetAcquisitionError as exc:
            raise SystemExit(str(exc)) from exc
        assets.append(asset)
        print(
            f"      -> {asset['provider']}:{asset['asset_id']} "
            f"query={asset['query']!r} type={asset['type']}"
        )

    manifest = {
        "schema_version": 1,
        "source_storyboard": storyboard_path.name,
        "scene_count": len(scenes),
        "acquisition_strategy": "scene_queries_in_order_then_generic_fallbacks",
        "assets": assets,
    }
    try:
        validate_manifest(manifest, storyboard)
    except AssetAcquisitionError as exc:
        raise SystemExit(f"Asset manifest validation failed: {exc}") from exc

    manifest_path = OUTPUT_DIR / f"asset_manifest_{timestamp}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    compatibility_path = OUTPUT_DIR / f"visuals_{timestamp}.json"
    compatibility_path.write_text(
        json.dumps(legacy_visuals(assets), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    save_used_ids([asset["asset_id"] for asset in assets if asset["provider"] == "pexels"])
    print(f"\n✅ M3 asset manifest: {manifest_path.name} ({len(assets)} scene assets)")
    print(f"   Compatibility manifest: {compatibility_path.name}")


if __name__ == "__main__":
    main()
