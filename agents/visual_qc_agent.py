"""Deterministic M5.5 visual-quality QC for Factory V1.

This module does not pretend to inspect image semantics. It verifies the
machine-auditable visual-selection contract that M5.1-M5.4 established:
candidate provenance, selected-asset linkage, technical portrait suitability,
duplicate/diversity limits, motion validity, renderer linkage and Source Card
readability invariants. It also writes a human-readable selection report.
"""

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
ALLOWED_STILL_MOTIONS = {"static", "slow_push_in", "slow_pull_out", "pan_left", "pan_right"}
MAX_SAME_CATEGORY_RUN = 2
MIN_PORTRAIT_WIDTH = 540
MIN_PORTRAIT_HEIGHT = 960
SOURCE_CARD_SAFE_BOTTOM_PX = 520


class VisualQCError(RuntimeError):
    pass


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VisualQCError(f"Invalid JSON {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise VisualQCError(f"{path.name} must contain a JSON object")
    return value


def _max_same_run(values: list[str]) -> int:
    if not values:
        return 0
    longest = current = 1
    for left, right in zip(values, values[1:]):
        current = current + 1 if left == right else 1
        longest = max(longest, current)
    return longest


def _candidate_map(pool: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for candidate in pool.get("ranked_candidates", []):
        asset_id = str(candidate.get("asset_id", ""))
        if not asset_id:
            raise VisualQCError("ranked candidate missing asset_id")
        if asset_id in result:
            raise VisualQCError(f"duplicate candidate asset_id inside scene pool: {asset_id}")
        result[asset_id] = candidate
    return result


def _selection_row(scene: dict, asset: dict, candidate: dict | None, segment: dict) -> dict:
    selection = asset.get("selection", {})
    return {
        "scene_id": int(scene["scene_id"]),
        "narration": str(scene.get("text", scene.get("narration", ""))).strip(),
        "visual_goal": str(scene.get("visual_goal", "")).strip(),
        "specificity_required": str(scene.get("specificity_required", "")),
        "asset_id": str(asset.get("asset_id", "")),
        "provider": str(asset.get("provider", "")),
        "source_url": str(asset.get("source_url", "")),
        "query": str(asset.get("query", asset.get("search_query", ""))),
        "rank": int(selection.get("rank", 1)),
        "final_score": float(selection.get("final_score", 0.0)),
        "technical_score": float(selection.get("technical_score", 0.0)),
        "semantic_score": float(selection.get("semantic_score", 0.0)),
        "penalty_total": float(selection.get("penalty_total", 0.0)),
        "visual_category": str(selection.get("visual_category", "")),
        "selection_reasons": [str(x) for x in selection.get("reasons", [])],
        "candidate_technical_status": None if candidate is None else candidate.get("technical_status"),
        "preferred_motion": str(asset.get("preferred_motion", "")),
        "resolved_motion": str(segment.get("resolved_motion", "")),
        "render_transform": str(segment.get("render_transform", "")),
    }


def run_visual_qc(timestamp: str) -> tuple[dict, Path, Path]:
    paths = {
        "storyboard": OUTPUT_DIR / f"storyboard_{timestamp}.json",
        "candidates": OUTPUT_DIR / f"candidate_manifest_{timestamp}.json",
        "assets": OUTPUT_DIR / f"asset_manifest_{timestamp}.json",
        "renderer": OUTPUT_DIR / f"renderer_manifest_{timestamp}.json",
        "final": OUTPUT_DIR / f"final_{timestamp}.mp4",
    }
    for path in paths.values():
        if not path.exists() or path.stat().st_size <= 0:
            raise VisualQCError(f"Required M5.5 artifact missing or empty: {path.name}")

    storyboard = _read_json(paths["storyboard"])
    candidates = _read_json(paths["candidates"])
    assets = _read_json(paths["assets"])
    renderer = _read_json(paths["renderer"])

    scenes = storyboard.get("scenes", [])
    pools = candidates.get("scenes", [])
    selected = assets.get("assets", [])
    segments = renderer.get("segments", [])
    count = len(scenes)
    if not (8 <= count <= 12):
        raise VisualQCError(f"scene count outside 8..12: {count}")
    if not (len(pools) == len(selected) == len(segments) == count):
        raise VisualQCError("storyboard/candidate/assets/renderer counts disagree")
    if candidates.get("milestone") != "M5.3":
        raise VisualQCError("candidate manifest is not the validated M5.3 contract")
    if assets.get("acquisition_strategy") != "semantic_ranked_with_global_diversity_penalties":
        raise VisualQCError("unexpected asset acquisition strategy")
    if renderer.get("milestone") != "M5.4":
        raise VisualQCError("renderer manifest is not M5.4")
    if renderer.get("source_card_strategy") != "concise_caption_safe_mobile_card":
        raise VisualQCError("unexpected Source Card strategy")

    seen_assets: set[str] = set()
    categories: list[str] = []
    rows: list[dict] = []
    source_cards = 0
    portrait_eligible_selected = 0

    for index, (scene, pool, asset, segment) in enumerate(zip(scenes, pools, selected, segments), start=1):
        ids = [int(scene.get("scene_id", -1)), int(pool.get("scene_id", -1)), int(asset.get("scene_id", -1)), int(segment.get("scene_id", -1))]
        if ids != [index, index, index, index]:
            raise VisualQCError(f"scene identity mismatch at position {index}: {ids}")

        asset_id = str(asset.get("asset_id", ""))
        if not asset_id or asset_id in seen_assets:
            raise VisualQCError(f"duplicate or missing selected asset at scene {index}: {asset_id!r}")
        seen_assets.add(asset_id)

        selection = asset.get("selection", {})
        category = str(selection.get("visual_category", "")).strip()
        if not category:
            raise VisualQCError(f"scene {index} selected asset has no visual category")
        categories.append(category)
        if not selection.get("reasons"):
            raise VisualQCError(f"scene {index} has no auditable selection reasons")

        preferred = str(asset.get("preferred_motion", ""))
        resolved = str(segment.get("resolved_motion", ""))
        if preferred not in ALLOWED_STILL_MOTIONS:
            raise VisualQCError(f"scene {index} invalid preferred motion: {preferred}")
        if asset.get("type") == "video":
            if resolved != "native_video":
                raise VisualQCError(f"scene {index} video must preserve native motion")
        elif resolved != preferred:
            raise VisualQCError(f"scene {index} still resolved motion differs from preferred motion")

        if str(segment.get("asset_id")) != asset_id:
            raise VisualQCError(f"scene {index} renderer selected a different asset")

        candidate = None
        if asset.get("provider") == "pexels":
            cmap = _candidate_map(pool)
            candidate = cmap.get(asset_id)
            if candidate is None:
                raise VisualQCError(f"scene {index} selected Pexels asset is absent from ranked candidate pool")
            if candidate.get("technical_status") != "eligible":
                raise VisualQCError(f"scene {index} selected candidate was not technically eligible")
            width = int(candidate.get("download_width") or 0)
            height = int(candidate.get("download_height") or 0)
            if width < MIN_PORTRAIT_WIDTH or height < MIN_PORTRAIT_HEIGHT or height <= width:
                raise VisualQCError(f"scene {index} selected candidate is not portrait-croppable: {width}x{height}")
            if int(selection.get("rank", -1)) != int(candidate.get("ranking", {}).get("rank", -2)):
                raise VisualQCError(f"scene {index} selected rank does not match candidate manifest")
            portrait_eligible_selected += 1
        elif asset.get("provider") == "source_article":
            source_cards += 1
            if preferred != "static" or resolved != "static":
                raise VisualQCError(f"scene {index} Source Card must remain static")
            if segment.get("render_transform") != "concise_caption_safe_source_card":
                raise VisualQCError(f"scene {index} Source Card transform missing")
        else:
            raise VisualQCError(f"scene {index} unsupported provider {asset.get('provider')!r}")

        rows.append(_selection_row(scene, asset, candidate, segment))

    max_category_run = _max_same_run(categories)
    if max_category_run > MAX_SAME_CATEGORY_RUN:
        raise VisualQCError(f"visual category repeats {max_category_run} times consecutively")

    checks = {
        "scene_count": count,
        "exact_selected_asset_duplicates": 0,
        "selected_asset_ids_unique": True,
        "max_same_visual_category_run": max_category_run,
        "max_allowed_same_visual_category_run": MAX_SAME_CATEGORY_RUN,
        "portrait_eligible_pexels_selected": portrait_eligible_selected,
        "source_card_count": source_cards,
        "source_card_strategy": "concise_caption_safe_mobile_card",
        "source_card_caption_safe_bottom_px": SOURCE_CARD_SAFE_BOTTOM_PX,
        "motion_parameters_valid": True,
        "candidate_to_asset_provenance_valid": True,
        "asset_to_renderer_provenance_valid": True,
        "selection_reasons_present": True,
        "final_video_present": True,
    }
    report = {
        "schema_version": 1,
        "milestone": "M5.5",
        "timestamp": timestamp,
        "status": "PASS",
        "checks": checks,
        "categories": categories,
        "selections": rows,
        "limitations": [
            "Visual QC is deterministic contract/provenance QC; it does not claim pixel-level semantic understanding.",
            "Semantic ranking evidence remains provider metadata/query-derived until a future explicitly approved image-understanding stage.",
        ],
    }
    json_path = OUTPUT_DIR / f"visual_qc_report_{timestamp}.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# M5.5 Visual Selection Report",
        "",
        f"Status: **PASS**  ",
        f"Scenes: **{count}**  ",
        f"Exact selected-asset duplicates: **0**  ",
        f"Maximum same-category run: **{max_category_run} / {MAX_SAME_CATEGORY_RUN}**  ",
        f"Source Cards: **{source_cards}**  ",
        "",
        "| Scene | Visual goal | Selected asset | Category | Score | Rank | Motion | Why selected |",
        "|---:|---|---|---|---:|---:|---|---|",
    ]
    for row in rows:
        reasons = "; ".join(row["selection_reasons"][:4]).replace("|", "/")
        goal = row["visual_goal"].replace("|", "/")
        asset_label = f"{row['provider']}:{row['asset_id']}".replace("|", "/")
        lines.append(
            f"| {row['scene_id']} | {goal} | {asset_label} | {row['visual_category']} | "
            f"{row['final_score']:.2f} | {row['rank']} | {row['resolved_motion']} | {reasons} |"
        )
    lines += [
        "",
        "## Deterministic QC scope",
        "",
        "This report proves selection provenance, technical portrait suitability, duplicate/diversity rules, motion validity, Source Card invariants and renderer linkage. It deliberately does not claim pixel-level semantic understanding.",
    ]
    markdown_path = OUTPUT_DIR / f"visual_selection_report_{timestamp}.md"
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report, json_path, markdown_path


if __name__ == "__main__":
    scripts = sorted(OUTPUT_DIR.glob("script_[0-9]*.json"))
    if not scripts:
        raise SystemExit("No script artifact found for M5.5 visual QC")
    stamp = scripts[-1].stem.replace("script_", "")
    try:
        result, json_report, selection_report = run_visual_qc(stamp)
    except VisualQCError as exc:
        raise SystemExit(f"M5.5 VISUAL QC FAILED: {exc}") from exc
    print(f"✅ M5.5 Visual QC PASS: {json_report.name}")
    print(f"✅ Visual selection report: {selection_report.name}")
    print(json.dumps(result["checks"], indent=2))
