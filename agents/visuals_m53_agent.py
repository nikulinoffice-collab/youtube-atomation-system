"""M5.3 runner: retrieve pools, rank eligible candidates, acquire ranked winners."""
import json
from collections import Counter
import requests
import visuals_agent as base
from visual_ranker import rank_scene, register


def selected_entry(scene, candidate, path):
    item = base.selected_entry(scene, candidate, path)
    rank = candidate["ranking"]
    item["selection"] = {
        "rank": rank["rank"], "final_score": rank["final_score"],
        "technical_score": rank["technical_score"], "semantic_score": rank["semantic_score"],
        "penalty_total": rank["penalty_total"], "visual_category": rank["visual_category"],
        "reasons": rank["reasons"],
    }
    return item


def acquire(scene, ranked, timestamp, source_url, reserved):
    if str(scene.get("preferred_asset_type")) == "source_card" and source_url:
        path = base.OUTPUT_DIR / f"visual_{timestamp}_scene_{int(scene['scene_id']):02d}_source.jpg"
        if base.capture_source_screenshot(source_url, path):
            item = base.source_entry(scene, source_url, path)
            item["selection"] = {"rank":1,"final_score":100.0,"technical_score":36.0,"semantic_score":64.0,"penalty_total":0.0,"visual_category":"source_card","reasons":["canonical source article"]}
            return item, None
        path.unlink(missing_ok=True)
    for candidate in ranked:
        asset_id = str(candidate["asset_id"])
        if asset_id in reserved:
            continue
        suffix = ".mp4" if candidate["type"] == "video" else ".jpg"
        path = base.OUTPUT_DIR / f"visual_{timestamp}_scene_{int(scene['scene_id']):02d}{suffix}"
        try:
            base.download_file(str(candidate["download_url"]), path)
        except (requests.RequestException, base.AssetAcquisitionError):
            path.unlink(missing_ok=True)
            continue
        reserved.add(asset_id)
        return selected_entry(scene, candidate, path), candidate
    raise base.AssetAcquisitionError(f"Scene {scene['scene_id']} has no downloadable ranked candidate")


def validate_ranked(manifest, storyboard):
    if manifest.get("schema_version") != 2 or manifest.get("milestone") != "M5.3":
        raise base.AssetAcquisitionError("invalid M5.3 candidate manifest header")
    if len(manifest.get("scenes", [])) != len(storyboard.get("scenes", [])):
        raise base.AssetAcquisitionError("M5.3 scene count mismatch")
    for scene, pool in zip(storyboard["scenes"], manifest["scenes"]):
        if int(pool.get("scene_id", -1)) != int(scene["scene_id"]):
            raise base.AssetAcquisitionError("M5.3 scene id mismatch")
        ranked = pool.get("ranked_candidates", [])
        if not ranked:
            raise base.AssetAcquisitionError(f"Scene {scene['scene_id']} has no ranked candidates")
        scores = [float(c["ranking"]["final_score"]) for c in ranked]
        if scores != sorted(scores, reverse=True):
            raise base.AssetAcquisitionError(f"Scene {scene['scene_id']} ranking order mismatch")
        for index, candidate in enumerate(ranked, 1):
            rank = candidate.get("ranking", {})
            if int(rank.get("rank", -1)) != index or not rank.get("reasons"):
                raise base.AssetAcquisitionError(f"Scene {scene['scene_id']} ranking audit missing")


def main():
    if not base.API_KEY:
        raise SystemExit("PEXELS_API_KEY is not set")
    storyboard_path = base.find_latest_storyboard()
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))
    scenes = storyboard.get("scenes", [])
    if not scenes:
        raise SystemExit("Storyboard contains no scenes")
    timestamp = storyboard_path.stem.replace("storyboard_", "")
    source_url = base.source_link_for_timestamp(timestamp)
    pools = [base.collect_scene_candidates(scene, source_url) for scene in scenes]

    previous, category_counts, creator_counts = [], Counter(), Counter()
    historical = set(base.load_used_ids())
    selected_ids, ranked_pools, assets = set(), [], []
    for scene, pool in zip(scenes, pools):
        ranked = rank_scene(scene, pool["candidates"], previous, category_counts, creator_counts, historical | selected_ids)
        if not ranked:
            raise SystemExit(f"Scene {scene['scene_id']} has no rankable candidates")
        ranked_pool = dict(pool)
        ranked_pool["ranked_candidates"] = ranked
        ranked_pools.append(ranked_pool)
        asset, winner = acquire(scene, ranked, timestamp, source_url, selected_ids)
        assets.append(asset)
        if winner:
            register(winner, previous, category_counts, creator_counts, historical)
            selected_ids.add(str(winner["asset_id"]))
        else:
            previous.append("source_card"); category_counts["source_card"] += 1
        print(f"scene {scene['scene_id']}: selected={asset['asset_id']} rank={asset['selection']['rank']} score={asset['selection']['final_score']}")

    candidate_manifest = {
        "schema_version":2, "milestone":"M5.3", "source_storyboard":storyboard_path.name,
        "scene_count":len(scenes),
        "retrieval_policy":{"semantic_ranking":True,"video_duration_must_cover_scene":True,"minimum_portrait_width":base.MIN_PORTRAIT_WIDTH,"minimum_portrait_height":base.MIN_PORTRAIT_HEIGHT},
        "ranking_policy":{"technical_score_max":36,"semantic_score_max":58,"query_semantic_contribution_is_capped":True,"candidate_specific_semantics":"provider URL slug and creator metadata","generic_penalty":True,"avoid_penalty":True,"duplicate_penalty":True,"creator_reuse_penalty":True,"global_diversity_penalty":True,"image_content_claims":False},
        "scenes":ranked_pools,
    }
    validate_ranked(candidate_manifest, storyboard)
    candidate_path = base.OUTPUT_DIR / f"candidate_manifest_{timestamp}.json"
    candidate_path.write_text(json.dumps(candidate_manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    asset_manifest = {"schema_version":3,"source_storyboard":storyboard_path.name,"source_candidate_manifest":candidate_path.name,"scene_count":len(scenes),"acquisition_strategy":"semantic_ranked_with_global_diversity_penalties","assets":assets}
    base.validate_manifest(asset_manifest, storyboard)
    asset_path = base.OUTPUT_DIR / f"asset_manifest_{timestamp}.json"
    asset_path.write_text(json.dumps(asset_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (base.OUTPUT_DIR / f"visuals_{timestamp}.json").write_text(json.dumps(base.legacy_visuals(assets), indent=2, ensure_ascii=False), encoding="utf-8")
    base.save_used_ids([a["asset_id"] for a in assets if a["provider"] == "pexels"])
    print(f"M5.3 PASS candidate_manifest={candidate_path.name} assets={len(assets)} categories={dict(category_counts)}")

if __name__ == "__main__":
    main()
