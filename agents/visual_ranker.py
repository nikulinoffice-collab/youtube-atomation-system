"""Auditable deterministic scoring for M5.3 visual candidate selection."""
from collections import Counter
import re
from urllib.parse import unquote, urlparse

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP = {"a","an","and","are","as","at","be","by","for","from","in","is","it","of","on","or","the","to","with","show","showing","visual","scene"}
GENERIC = {"technology","computer","digital","network","office","business","work","working","laptop","screen","abstract","data"}
CATEGORIES = {
    "meeting": {"meeting","boardroom","conference","discussion","team","executive"},
    "screen": {"laptop","computer","screen","monitor","desktop","typing"},
    "stage": {"stage","speaker","keynote","podium","audience","presentation"},
    "coding": {"code","coding","programmer","developer","terminal","software"},
    "data": {"chart","analytics","dashboard","finance","trading","graph"},
    "person": {"portrait","face","founder","ceo","woman","man"},
    "environment": {"building","city","server","datacenter","factory","office"},
    "abstract": {"abstract","ai","hologram","futuristic","digital","network"},
}


def words(value):
    return {w for w in TOKEN_RE.findall(str(value or "").casefold()) if len(w) >= 2 and w not in STOP}


def many_words(values):
    out = set()
    if isinstance(values, list):
        for value in values:
            out |= words(value)
    return out


def slug_words(url):
    try:
        path = unquote(urlparse(str(url)).path).replace("-", " ").replace("_", " ")
    except Exception:
        path = str(url)
    return words(path)


def contract(scene):
    return {
        "goal": words(scene.get("visual_goal")),
        "must": many_words(scene.get("must_show")),
        "avoid": many_words(scene.get("avoid")),
        "subject": words(scene.get("subject")),
        "action": words(scene.get("action")),
        "environment": words(scene.get("environment")),
    }


def overlap(evidence, target):
    return 0.0 if not target else len(evidence & target) / len(target)


def evidence(candidate):
    provider = slug_words(candidate.get("source_url")) | words(candidate.get("creator"))
    query = words(candidate.get("query"))
    return provider, query, provider | query


def category_for(scene, candidate):
    provider, query, combined = evidence(candidate)
    combined |= words(scene.get("subject")) | words(scene.get("environment"))
    best = max(((len(combined & vocab), name) for name, vocab in CATEGORIES.items()), default=(0, "other"))
    return best[1] if best[0] else str(scene.get("shot_type") or "other")


def score(scene, candidate, previous_categories, category_counts, creator_counts, used_ids):
    c = contract(scene)
    required = c["subject"] | c["action"] | c["environment"] | c["must"]
    provider, query, combined = evidence(candidate)

    width = max(1, int(candidate.get("download_width") or 0))
    height = max(1, int(candidate.get("download_height") or 0))
    target_ratio = 9 / 16
    ratio_error = abs(width / height - target_ratio) / target_ratio
    crop = max(0.0, 16.0 * (1.0 - min(1.0, ratio_error)))
    resolution = min(10.0, 10.0 * width * height / (1080 * 1920))
    preferred = str(scene.get("preferred_asset_type", "either"))
    asset_type = str(candidate.get("type", ""))
    type_score = 6.0 if preferred == asset_type else (4.0 if preferred == "either" else 1.5)
    duration_score = 4.0
    if asset_type == "video":
        required_duration = max(0.1, float(scene.get("duration") or 0.1))
        duration = float(candidate.get("provider_duration") or 0.0)
        duration_score = 2.0 + 2.0 * min(1.0, max(0.0, (duration - required_duration) / required_duration))
    technical = min(36.0, crop + resolution + type_score + duration_score)

    provider_required = overlap(provider, required)
    provider_goal = overlap(provider, c["goal"])
    provider_must = overlap(provider, c["must"])
    query_required = min(0.75, overlap(query, required))
    dimensions = sum(bool(provider & c[key]) for key in ("subject", "action", "environment"))
    semantic = min(58.0, 24*provider_required + 10*provider_goal + 10*provider_must + 8*query_required + 2*dimensions)

    specificity = str(scene.get("specificity_required", "medium"))
    generic_hits = combined & GENERIC
    generic_penalty = 0.0
    if generic_hits and provider_required < 0.20:
        generic_penalty = {"low":2.0,"medium":6.0,"high":11.0}.get(specificity,6.0)
    avoid_hits = combined & c["avoid"]
    avoid_penalty = min(16.0, 5.0 * len(avoid_hits))
    asset_id = str(candidate.get("asset_id", ""))
    duplicate_penalty = 100.0 if asset_id in used_ids else 0.0
    creator = str(candidate.get("creator", "")).casefold().strip()
    creator_penalty = min(6.0, 2.0 * creator_counts.get(creator, 0)) if creator else 0.0
    category = category_for(scene, candidate)
    consecutive_penalty = 0.0
    if previous_categories and previous_categories[-1] == category:
        consecutive_penalty = 8.0
        if len(previous_categories) >= 2 and previous_categories[-2] == category:
            consecutive_penalty = 16.0
    category_penalty = min(8.0, 2.0 * category_counts.get(category, 0))
    total_penalty = generic_penalty + avoid_penalty + duplicate_penalty + creator_penalty + consecutive_penalty + category_penalty
    final = technical + semantic - total_penalty

    ranked = dict(candidate)
    ranked["ranking"] = {
        "technical_score": round(technical,3),
        "semantic_score": round(semantic,3),
        "penalty_total": round(total_penalty,3),
        "final_score": round(final,3),
        "visual_category": category,
        "provider_required_coverage": round(provider_required,4),
        "provider_goal_coverage": round(provider_goal,4),
        "provider_must_show_coverage": round(provider_must,4),
        "query_required_coverage_capped": round(query_required,4),
        "generic_hits": sorted(generic_hits),
        "avoid_hits": sorted(avoid_hits),
        "reasons": [
            f"technical={technical:.1f}/36",
            f"provider_required={provider_required:.2f}",
            f"provider_goal={provider_goal:.2f}",
            f"provider_must_show={provider_must:.2f}",
            f"query_required_capped={query_required:.2f}",
            f"generic_penalty=-{generic_penalty:.1f}",
            f"avoid_penalty=-{avoid_penalty:.1f}",
            f"diversity_penalty=-{consecutive_penalty + category_penalty:.1f}",
            f"creator_penalty=-{creator_penalty:.1f}",
        ],
    }
    return ranked


def rank_scene(scene, candidates, previous_categories, category_counts, creator_counts, used_ids):
    ranked = [score(scene, c, previous_categories, category_counts, creator_counts, used_ids) for c in candidates if c.get("technical_status") == "eligible"]
    ranked.sort(key=lambda c: (-float(c["ranking"]["final_score"]), -float(c["ranking"]["semantic_score"]), -float(c["ranking"]["technical_score"]), str(c.get("asset_id", ""))))
    for index, candidate in enumerate(ranked, 1):
        candidate["ranking"]["rank"] = index
    return ranked


def register(candidate, previous_categories, category_counts, creator_counts, used_ids):
    category = str(candidate["ranking"]["visual_category"])
    previous_categories.append(category)
    category_counts[category] += 1
    creator = str(candidate.get("creator", "")).casefold().strip()
    if creator:
        creator_counts[creator] += 1
    used_ids.add(str(candidate.get("asset_id", "")))
