"""M5.2 Candidate Retrieval for Factory V1 semantic visuals.

Consumes storyboard_<timestamp>.json, expands each scene's M5.1 query strategies,
retrieves multiple Pexels candidates, applies deterministic technical filters, and
writes candidate_manifest_<timestamp>.json before acquiring one compatibility asset
per scene. M5.2 deliberately does NOT rank semantic quality: until M5.3 the selected
asset is the first technically eligible candidate in deterministic strategy order.
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
SEARCH_PAGES = [1]
PER_PAGE = 10
MAX_CANDIDATES_PER_QUERY = 6
MAX_SCENE_CANDIDATES = 30
MIN_PORTRAIT_WIDTH = 540
MIN_PORTRAIT_HEIGHT = 960
MIN_CANDIDATES_BEFORE_ALTERNATE_TYPE = 4


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
        and int(item.get("width") or 0) >= MIN_PORTRAIT_WIDTH
        and int(item.get("height") or 0) >= MIN_PORTRAIT_HEIGHT
        and int(item.get("height") or 0) > int(item.get("width") or 0)
        and item.get("link")
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            abs(int(item.get("width") or 0) - 720),
            -int(item.get("height") or 0),
        )
    )
    return candidates[0]


def query_strategies(scene: dict) -> list[dict]:
    raw = scene.get("query_strategies")
    strategies: list[dict] = []
    seen: set[str] = set()
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            strategy = str(item.get("strategy", "")).strip()
            query = str(item.get("query", "")).strip()
            key = query.casefold()
            if strategy and len(query) >= 3 and key not in seen:
                seen.add(key)
                strategies.append({"strategy": strategy, "query": query})
    if len(strategies) < 3:
        legacy = scene.get("search_queries")
        if isinstance(legacy, list):
            for value in legacy:
                query = str(value).strip()
                key = query.casefold()
                if len(query) >= 3 and key not in seen:
                    seen.add(key)
                    strategies.append({"strategy": "legacy", "query": query})
    if len(strategies) < 3:
        raise AssetAcquisitionError(
            f"Scene {scene.get('scene_id')} requires at least three usable query strategies."
        )
    return strategies[:5]


def fallback_strategies(scene: dict) -> list[dict]:
    existing = {item["query"].casefold() for item in query_strategies(scene)}
    return [
        {"strategy": "generic_fallback", "query": query}
        for query in GENERIC_FALLBACKS
        if query.casefold() not in existing
    ]


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


def technical_rejection(width: int, height: int, duration: float | None, required_duration: float) -> str | None:
    if width < MIN_PORTRAIT_WIDTH or height < MIN_PORTRAIT_HEIGHT:
        return "resolution_below_minimum"
    if height <= width:
        return "not_portrait_crop_suitable"
    if duration is not None and duration + 1e-6 < required_duration:
        return "video_shorter_than_scene"
    return None


def video_candidate(scene: dict, video: dict, file_info: dict, strategy: str, query: str, page: int) -> dict:
    width = int(file_info.get("width") or 0)
    height = int(file_info.get("height") or 0)
    duration = float(video.get("duration") or 0.0)
    rejection = technical_rejection(width, height, duration, float(scene["duration"]))
    return {
        "provider": "pexels",
        "type": "video",
        "asset_id": str(video.get("id", "")),
        "strategy": strategy,
        "query": query,
        "query_page": page,
        "source_url": str(video.get("url", "")),
        "creator": str(video.get("user", {}).get("name", "")),
        "creator_url": str(video.get("user", {}).get("url", "")),
        "provider_duration": duration,
        "download_width": width,
        "download_height": height,
        "download_url": str(file_info.get("link", "")),
        "technical_status": "rejected" if rejection else "eligible",
        "technical_rejection": rejection,
    }


def photo_candidate(scene: dict, photo: dict, strategy: str, query: str, page: int) -> dict:
    width = int(photo.get("width") or 0)
    height = int(photo.get("height") or 0)
    rejection = technical_rejection(width, height, None, float(scene["duration"]))
    src = photo.get("src", {}) if isinstance(photo.get("src"), dict) else {}
    download_url = src.get("large2x") or src.get("large") or src.get("portrait") or ""
    if not download_url and rejection is None:
        rejection = "missing_download_url"
    numeric_id = str(photo.get("id", ""))
    return {
        "provider": "pexels",
        "type": "image",
        "asset_id": f"photo_{numeric_id}" if numeric_id else "",
        "strategy": strategy,
        "query": query,
        "query_page": page,
        "source_url": str(photo.get("url", "")),
        "creator": str(photo.get("photographer", "")),
        "creator_url": str(photo.get("photographer_url", "")),
        "provider_duration": None,
        "download_width": width,
        "download_height": height,
        "download_url": str(download_url),
        "technical_status": "rejected" if rejection else "eligible",
        "technical_rejection": rejection,
    }


def collect_kind_candidates(scene: dict, kind: str, strategies: list[dict], seen_ids: set[str]) -> tuple[list[dict], list[dict]]:
    candidates: list[dict] = []
    attempts: list[dict] = []
    for strategy_item in strategies:
        if len(candidates) >= MAX_SCENE_CANDIDATES:
            break
        strategy = str(strategy_item["strategy"])
        query = str(strategy_item["query"])
        query_seen = 0
        query_eligible = 0
        query_rejected = 0
        for page in SEARCH_PAGES:
            try:
                results = search_videos(query, page) if kind == "video" else search_photos(query, page)
            except (requests.RequestException, AssetAcquisitionError) as exc:
                attempts.append({
                    "strategy": strategy,
                    "query": query,
                    "kind": kind,
                    "page": page,
                    "status": "search_error",
                    "error": str(exc),
                })
                continue
            for raw in results:
                if query_seen >= MAX_CANDIDATES_PER_QUERY or len(candidates) >= MAX_SCENE_CANDIDATES:
                    break
                if kind == "video":
                    file_info = best_video_file(raw)
                    if not file_info:
                        query_rejected += 1
                        query_seen += 1
                        continue
                    candidate = video_candidate(scene, raw, file_info, strategy, query, page)
                else:
                    candidate = photo_candidate(scene, raw, strategy, query, page)
                query_seen += 1
                asset_id = str(candidate.get("asset_id", ""))
                if not asset_id or asset_id in seen_ids:
                    continue
                seen_ids.add(asset_id)
                candidates.append(candidate)
                if candidate["technical_status"] == "eligible":
                    query_eligible += 1
                else:
                    query_rejected += 1
        attempts.append({
            "strategy": strategy,
            "query": query,
            "kind": kind,
            "status": "completed",
            "candidates_seen": query_seen,
            "eligible": query_eligible,
            "rejected": query_rejected,
        })
    return candidates, attempts


def preferred_kind_order(scene: dict) -> list[str]:
    preferred = str(scene.get("preferred_asset_type", "either"))
    if preferred == "image":
        return ["image", "video"]
    return ["video", "image"]


def collect_scene_candidates(scene: dict, source_url: str) -> dict:
    preferred = str(scene.get("preferred_asset_type", "either"))
    if preferred == "source_card" and source_url:
        return {
            "scene_id": int(scene["scene_id"]),
            "visual_goal": str(scene.get("visual_goal", scene.get("visual_intent", ""))),
            "preferred_asset_type": preferred,
            "query_strategies": query_strategies(scene),
            "search_attempts": [],
            "candidates": [{
                "provider": "source_article",
                "type": "image",
                "asset_id": f"source_scene_{scene['scene_id']}",
                "strategy": "source_article",
                "query": "source_article",
                "query_page": None,
                "source_url": source_url,
                "creator": "",
                "creator_url": "",
                "provider_duration": None,
                "download_width": 1080,
                "download_height": 1920,
                "download_url": source_url,
                "technical_status": "eligible",
                "technical_rejection": None,
            }],
        }

    strategies = query_strategies(scene)
    seen_ids: set[str] = set()
    all_candidates: list[dict] = []
    attempts: list[dict] = []
    order = preferred_kind_order(scene)
    first_candidates, first_attempts = collect_kind_candidates(scene, order[0], strategies, seen_ids)
    all_candidates.extend(first_candidates)
    attempts.extend(first_attempts)
    eligible_first = sum(c["technical_status"] == "eligible" for c in first_candidates)

    if eligible_first < MIN_CANDIDATES_BEFORE_ALTERNATE_TYPE:
        second_candidates, second_attempts = collect_kind_candidates(scene, order[1], strategies, seen_ids)
        all_candidates.extend(second_candidates)
        attempts.extend(second_attempts)

    if not any(c["technical_status"] == "eligible" for c in all_candidates):
        fallback = fallback_strategies(scene)
        for kind in order:
            fallback_candidates, fallback_attempts = collect_kind_candidates(scene, kind, fallback, seen_ids)
            all_candidates.extend(fallback_candidates)
            attempts.extend(fallback_attempts)
            if any(c["technical_status"] == "eligible" for c in all_candidates):
                break

    return {
        "scene_id": int(scene["scene_id"]),
        "visual_goal": str(scene.get("visual_goal", scene.get("visual_intent", ""))),
        "preferred_asset_type": preferred,
        "query_strategies": strategies,
        "search_attempts": attempts,
        "candidates": all_candidates[:MAX_SCENE_CANDIDATES],
    }


def validate_candidate_manifest(manifest: dict, storyboard: dict) -> None:
    scenes = storyboard.get("scenes")
    scene_entries = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise AssetAcquisitionError("Storyboard has no scenes.")
    if not isinstance(scene_entries, list) or len(scene_entries) != len(scenes):
        raise AssetAcquisitionError("Candidate manifest must contain one entry per storyboard scene.")
    if int(manifest.get("scene_count", -1)) != len(scenes):
        raise AssetAcquisitionError("Candidate manifest scene_count mismatch.")
    for scene, entry in zip(scenes, scene_entries):
        scene_id = int(scene["scene_id"])
        if int(entry.get("scene_id", -1)) != scene_id:
            raise AssetAcquisitionError("Candidate manifest scene order/id mismatch.")
        strategies = entry.get("query_strategies")
        if not isinstance(strategies, list) or not (3 <= len(strategies) <= 5):
            raise AssetAcquisitionError(f"Scene {scene_id} has invalid candidate query strategies.")
        candidates = entry.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise AssetAcquisitionError(f"Scene {scene_id} has no retrieved candidates.")
        eligible = [c for c in candidates if c.get("technical_status") == "eligible"]
        if not eligible:
            raise AssetAcquisitionError(f"Scene {scene_id} has no technically eligible candidate.")
        ids = [str(c.get("asset_id", "")) for c in candidates]
        if any(not asset_id for asset_id in ids) or len(ids) != len(set(ids)):
            raise AssetAcquisitionError(f"Scene {scene_id} candidate IDs are missing or duplicated.")
        for candidate in candidates:
            if not str(candidate.get("source_url", "")).strip():
                raise AssetAcquisitionError(f"Scene {scene_id} candidate lacks provenance source_url.")
            if candidate.get("technical_status") not in {"eligible", "rejected"}:
                raise AssetAcquisitionError(f"Scene {scene_id} candidate has invalid technical_status.")


def source_entry(scene: dict, source_url: str, path: Path) -> dict:
    return {
        "scene_id": int(scene["scene_id"]),
        "scene_start": float(scene["start"]),
        "scene_end": float(scene["end"]),
        "required_duration": float(scene["duration"]),
        "visual_intent": str(scene["visual_intent"]),
        "visual_goal": str(scene.get("visual_goal", scene["visual_intent"])),
        "preferred_asset_type": str(scene.get("preferred_asset_type", "source_card")),
        "path": str(path),
        "type": "image",
        "provider": "source_article",
        "asset_id": f"source_scene_{scene['scene_id']}",
        "query": "source_article",
        "query_strategy": "source_article",
        "query_page": None,
        "source_url": source_url,
        "creator": "",
        "creator_url": "",
        "provider_duration": None,
        "download_width": 1080,
        "download_height": 1920,
    }


def selected_entry(scene: dict, candidate: dict, path: Path) -> dict:
    return {
        "scene_id": int(scene["scene_id"]),
        "scene_start": float(scene["start"]),
        "scene_end": float(scene["end"]),
        "required_duration": float(scene["duration"]),
        "visual_intent": str(scene["visual_intent"]),
        "visual_goal": str(scene.get("visual_goal", scene["visual_intent"])),
        "preferred_asset_type": str(scene.get("preferred_asset_type", "either")),
        "path": str(path),
        "type": str(candidate["type"]),
        "provider": str(candidate["provider"]),
        "asset_id": str(candidate["asset_id"]),
        "query": str(candidate["query"]),
        "query_strategy": str(candidate["strategy"]),
        "query_page": candidate.get("query_page"),
        "source_url": str(candidate["source_url"]),
        "creator": str(candidate.get("creator", "")),
        "creator_url": str(candidate.get("creator_url", "")),
        "provider_duration": candidate.get("provider_duration"),
        "download_width": candidate.get("download_width"),
        "download_height": candidate.get("download_height"),
    }


def acquire_from_candidates(scene: dict, scene_pool: dict, timestamp: str, source_url: str, used: set[str], reserved: set[str]) -> dict:
    preferred = str(scene.get("preferred_asset_type", "either"))
    if preferred == "source_card" and source_url:
        path = OUTPUT_DIR / f"visual_{timestamp}_scene_{int(scene['scene_id']):02d}_source.jpg"
        print(f"   scene {scene['scene_id']}: source article")
        if capture_source_screenshot(source_url, path):
            return source_entry(scene, source_url, path)
        path.unlink(missing_ok=True)

    candidates = scene_pool.get("candidates", [])
    order = preferred_kind_order(scene)
    ordered = [
        candidate
        for kind in order
        for candidate in candidates
        if candidate.get("type") == kind and candidate.get("technical_status") == "eligible"
    ]
    for candidate in ordered:
        asset_id = str(candidate["asset_id"])
        if asset_id in used or asset_id in reserved:
            continue
        extension = ".mp4" if candidate["type"] == "video" else ".jpg"
        path = OUTPUT_DIR / f"visual_{timestamp}_scene_{int(scene['scene_id']):02d}{extension}"
        try:
            download_file(str(candidate["download_url"]), path)
        except (requests.RequestException, AssetAcquisitionError) as exc:
            print(f"   candidate download failed id={asset_id}: {exc}")
            path.unlink(missing_ok=True)
            continue
        reserved.add(asset_id)
        return selected_entry(scene, candidate, path)
    raise AssetAcquisitionError(
        f"Scene {scene['scene_id']} failed closed: candidate pool has no downloadable unused eligible asset."
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

    print(f"🎞️ M5.2 candidate retrieval: {len(scenes)} storyboard scenes")
    candidate_scenes: list[dict] = []
    for scene in scenes:
        try:
            scene_pool = collect_scene_candidates(scene, source_url)
        except AssetAcquisitionError as exc:
            raise SystemExit(str(exc)) from exc
        candidate_scenes.append(scene_pool)
        eligible = sum(c.get("technical_status") == "eligible" for c in scene_pool["candidates"])
        print(
            f"   scene {scene['scene_id']}: candidates={len(scene_pool['candidates'])} "
            f"eligible={eligible}"
        )

    candidate_manifest = {
        "schema_version": 1,
        "milestone": "M5.2",
        "source_storyboard": storyboard_path.name,
        "scene_count": len(scenes),
        "retrieval_policy": {
            "queries": "M5.1 query_strategies in deterministic order",
            "pages": SEARCH_PAGES,
            "per_page": PER_PAGE,
            "max_candidates_per_query": MAX_CANDIDATES_PER_QUERY,
            "max_scene_candidates": MAX_SCENE_CANDIDATES,
            "minimum_portrait_width": MIN_PORTRAIT_WIDTH,
            "minimum_portrait_height": MIN_PORTRAIT_HEIGHT,
            "video_duration_must_cover_scene": True,
            "semantic_ranking": False,
        },
        "scenes": candidate_scenes,
    }
    try:
        validate_candidate_manifest(candidate_manifest, storyboard)
    except AssetAcquisitionError as exc:
        raise SystemExit(f"Candidate manifest validation failed: {exc}") from exc

    candidate_manifest_path = OUTPUT_DIR / f"candidate_manifest_{timestamp}.json"
    candidate_manifest_path.write_text(
        json.dumps(candidate_manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    used = load_used_ids()
    reserved: set[str] = set()
    assets: list[dict] = []
    for scene, scene_pool in zip(scenes, candidate_scenes):
        try:
            asset = acquire_from_candidates(scene, scene_pool, timestamp, source_url, used, reserved)
        except AssetAcquisitionError as exc:
            raise SystemExit(str(exc)) from exc
        assets.append(asset)
        print(
            f"      selected compatibility asset -> {asset['provider']}:{asset['asset_id']} "
            f"strategy={asset.get('query_strategy')!r} query={asset['query']!r} type={asset['type']}"
        )

    manifest = {
        "schema_version": 2,
        "source_storyboard": storyboard_path.name,
        "source_candidate_manifest": candidate_manifest_path.name,
        "scene_count": len(scenes),
        "acquisition_strategy": "first_technically_eligible_candidate_pending_M5.3_ranking",
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
    print(f"\n✅ M5.2 candidate manifest: {candidate_manifest_path.name}")
    print(f"✅ Asset manifest: {manifest_path.name} ({len(assets)} selected scene assets)")
    print(f"   Compatibility manifest: {compatibility_path.name}")


if __name__ == "__main__":
    main()
