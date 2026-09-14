"""Storyboard Agent with deterministic timing and semantic Gemini enrichment.

Python owns scene boundaries. It uses dynamic programming over canonical word timings
to produce 8-12 contiguous scenes within hard duration limits, preferring punctuation,
pauses and ~3-second beats. Gemini can only enrich those fixed scenes with semantic
metadata. One semantic repair pass is allowed; malformed metadata fails closed.
"""

import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors

load_dotenv()

OUTPUT_DIR = Path(__file__).parent / "output"
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
MIN_SCENES = 8
MAX_SCENES = 12
MIN_SCENE_SECONDS = 1.2
MAX_SCENE_SECONDS = 6.0
TARGET_SCENE_SECONDS = 3.1
MIN_QUERIES = 2
MAX_QUERIES = 4
ALLOWED_PURPOSES = {
    "hook", "source", "fact", "context", "person_company", "claim",
    "counterargument", "evidence", "consequence", "payoff", "transition",
}
ALLOWED_ASSET_TYPES = {"video", "image", "either", "source_card"}


class StoryboardValidationError(ValueError):
    pass


def find_latest_timeline() -> Path:
    files = sorted(OUTPUT_DIR.glob("narration_timeline_*.json"))
    if not files:
        raise SystemExit("No narration_timeline_*.json found. Run voice_agent.py first.")
    return files[-1]


def canonical_scene_text(words: list[dict], start_word: int, end_word: int) -> str:
    return "".join(
        str(w.get("separator_before", "")) + str(w["word"])
        for w in words[start_word : end_word + 1]
    ).strip()


def boundary_bonus(words: list[dict], end_word: int) -> float:
    """Lower DP cost for natural semantic boundaries."""
    token = str(words[end_word]["word"]).rstrip()
    bonus = 0.0
    if re.search(r"[.!?][\"'’”)]*$", token):
        bonus -= 2.4
    elif re.search(r"[:;][\"'’”)]*$", token):
        bonus -= 1.2
    elif re.search(r",[\"'’”)]*$", token):
        bonus -= 0.5
    if end_word + 1 < len(words):
        gap = float(words[end_word + 1]["start"]) - float(words[end_word]["end"])
        if gap >= 0.35:
            bonus -= 1.0
        elif gap >= 0.20:
            bonus -= 0.4
    return bonus


def segment_cost(words: list[dict], start_word: int, end_word: int) -> float | None:
    duration = float(words[end_word]["end"]) - float(words[start_word]["start"])
    if duration < MIN_SCENE_SECONDS or duration > MAX_SCENE_SECONDS:
        return None
    duration_cost = (duration - TARGET_SCENE_SECONDS) ** 2
    edge_penalty = 0.0
    if duration < 2.0:
        edge_penalty += (2.0 - duration) * 1.5
    if duration > 4.3:
        edge_penalty += (duration - 4.3) * 1.1
    return duration_cost + edge_penalty + boundary_bonus(words, end_word)


def deterministic_partition(timeline: dict) -> list[dict]:
    """Find the lowest-cost feasible 8-12 scene partition via dynamic programming."""
    words = timeline.get("words")
    if not isinstance(words, list) or not words:
        raise StoryboardValidationError("Narration timeline contains no words.")
    n = len(words)
    speech_duration = float(words[-1]["end"]) - float(words[0]["start"])
    preferred_count = min(MAX_SCENES, max(MIN_SCENES, round(speech_duration / TARGET_SCENE_SECONDS)))

    best_overall: tuple[float, list[tuple[int, int]]] | None = None
    for scene_count in range(MIN_SCENES, MAX_SCENES + 1):
        # dp[k][i] = (cost, ranges), covering words [0, i) with k scenes.
        dp: list[dict[int, tuple[float, list[tuple[int, int]]]]] = [dict() for _ in range(scene_count + 1)]
        dp[0][0] = (0.0, [])
        for k in range(scene_count):
            for start_exclusive, (base_cost, ranges) in list(dp[k].items()):
                start_word = start_exclusive
                # leave at least one word for each remaining scene
                max_end = n - (scene_count - k - 1) - 1
                for end_word in range(start_word, max_end + 1):
                    cost = segment_cost(words, start_word, end_word)
                    if cost is None:
                        continue
                    next_i = end_word + 1
                    candidate = (base_cost + cost, ranges + [(start_word, end_word)])
                    existing = dp[k + 1].get(next_i)
                    if existing is None or candidate[0] < existing[0]:
                        dp[k + 1][next_i] = candidate
        complete = dp[scene_count].get(n)
        if complete is None:
            continue
        count_penalty = abs(scene_count - preferred_count) * 0.35
        candidate_total = complete[0] + count_penalty
        if best_overall is None or candidate_total < best_overall[0]:
            best_overall = (candidate_total, complete[1])

    if best_overall is None:
        raise StoryboardValidationError(
            f"No feasible {MIN_SCENES}-{MAX_SCENES} scene partition satisfies "
            f"{MIN_SCENE_SECONDS}-{MAX_SCENE_SECONDS}s hard duration bounds."
        )

    result = []
    for scene_id, (start_word, end_word) in enumerate(best_overall[1], start=1):
        start = float(words[start_word]["start"])
        end = float(words[end_word]["end"])
        result.append({
            "scene_id": scene_id,
            "start_word": start_word,
            "end_word": end_word,
            "start": round(start, 4),
            "end": round(end, 4),
            "duration": round(end - start, 4),
            "narration": canonical_scene_text(words, start_word, end_word),
        })
    validate_fixed_ranges(result, words)
    return result


def validate_fixed_ranges(scenes: list[dict], words: list[dict]) -> None:
    if not (MIN_SCENES <= len(scenes) <= MAX_SCENES):
        raise StoryboardValidationError("Deterministic partition scene count is invalid.")
    expected = 0
    for scene in scenes:
        if int(scene["start_word"]) != expected:
            raise StoryboardValidationError("Deterministic scene ranges are not contiguous.")
        duration = float(scene["duration"])
        if duration < MIN_SCENE_SECONDS - 1e-6 or duration > MAX_SCENE_SECONDS + 1e-6:
            raise StoryboardValidationError("Deterministic scene violates hard duration bounds.")
        expected = int(scene["end_word"]) + 1
    if expected != len(words):
        raise StoryboardValidationError("Deterministic partition does not cover all words.")


def extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise StoryboardValidationError("Storyboard response must be one JSON object.")
    return data


def normalize_queries(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise StoryboardValidationError("search_queries must be an array.")
    queries = [str(q).strip() for q in value]
    if not (MIN_QUERIES <= len(queries) <= MAX_QUERIES):
        raise StoryboardValidationError(f"Each scene requires {MIN_QUERIES}-{MAX_QUERIES} queries.")
    if any(len(q) < 3 or len(q) > 120 for q in queries):
        raise StoryboardValidationError("Search queries must be 3-120 characters.")
    if len({q.casefold() for q in queries}) != len(queries):
        raise StoryboardValidationError("Search queries must be unique within a scene.")
    return queries


def enrich_and_validate(raw: dict, fixed_scenes: list[dict], timeline: dict, source_timeline: str) -> dict:
    raw_scenes = raw.get("scenes")
    if not isinstance(raw_scenes, list) or len(raw_scenes) != len(fixed_scenes):
        raise StoryboardValidationError(
            f"Semantic response must contain exactly {len(fixed_scenes)} scenes."
        )
    enriched = []
    for fixed, meta in zip(fixed_scenes, raw_scenes):
        if not isinstance(meta, dict) or int(meta.get("scene_id", -1)) != fixed["scene_id"]:
            raise StoryboardValidationError(
                f"Semantic scene IDs must be exactly 1..{len(fixed_scenes)} in order."
            )
        purpose = str(meta.get("purpose", "")).strip()
        if purpose not in ALLOWED_PURPOSES:
            raise StoryboardValidationError(f"Scene {fixed['scene_id']} has invalid purpose {purpose!r}.")
        visual_intent = str(meta.get("visual_intent", "")).strip()
        if len(visual_intent) < 12 or len(visual_intent) > 240:
            raise StoryboardValidationError(
                f"Scene {fixed['scene_id']} visual_intent must be 12-240 characters."
            )
        if visual_intent.casefold() in {"ai", "artificial intelligence", "technology", "tech"}:
            raise StoryboardValidationError(f"Scene {fixed['scene_id']} visual_intent is too generic.")
        asset_type = str(meta.get("preferred_asset_type", "either")).strip()
        if asset_type not in ALLOWED_ASSET_TYPES:
            raise StoryboardValidationError(f"Scene {fixed['scene_id']} has invalid asset type.")
        enriched.append({
            **fixed,
            "purpose": purpose,
            "visual_intent": visual_intent,
            "search_queries": normalize_queries(meta.get("search_queries")),
            "preferred_asset_type": asset_type,
        })

    return {
        "schema_version": 2,
        "timing_strategy": "deterministic_dp",
        "source_timeline": source_timeline,
        "model": MODEL,
        "duration": float(timeline["duration"]),
        "speech_start": float(timeline["speech_start"]),
        "speech_end": float(timeline["speech_end"]),
        "scene_count": len(enriched),
        "scenes": enriched,
    }


def fixed_scene_prompt(scenes: list[dict]) -> str:
    return "\n".join(
        f"Scene {s['scene_id']} | FIXED words {s['start_word']}-{s['end_word']} | "
        f"{s['start']:.2f}-{s['end']:.2f}s | narration: {s['narration']}"
        for s in scenes
    )


def build_prompt(fixed_scenes: list[dict]) -> str:
    return f"""You are the semantic storyboard planner for a vertical AI/tech news Short.
Python has already fixed valid scene boundaries. YOU MUST NOT change, split, merge, or
renumber them. Add semantic metadata only.

FIXED SCENES:
{fixed_scene_prompt(fixed_scenes)}

For every scene:
- scene_id must match exactly.
- purpose: one of {', '.join(sorted(ALLOWED_PURPOSES))}.
- visual_intent: a concrete visible subject/action/location matching that scene's narration.
  Never use generic 'AI' or vague abstract filler when a concrete subject is possible.
- search_queries: 2-4 concise Pexels-friendly queries, specific first then broader fallback.
- preferred_asset_type: video, image, either, or source_card.
- Use source_card only if the scene explicitly refers to the source/article/news report.

Return ONLY JSON. Do not include timing or word-index fields:
{{"scenes":[{{"scene_id":1,"purpose":"hook","visual_intent":"...",
"search_queries":["...","..."],"preferred_asset_type":"video"}}]}}
"""


def build_repair_prompt(fixed_scenes: list[dict], prior: str, error: str) -> str:
    return f"""Your semantic storyboard metadata failed validation. You have exactly ONE repair.
Do not change the fixed number/order of scenes. Return complete corrected JSON only.

ERROR: {error}
PREVIOUS RESPONSE:
{prior}

CONTRACT:
{build_prompt(fixed_scenes)}
"""


def call_gemini(client, prompt: str, max_attempts: int = 4):
    delay = 15
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(model=MODEL, contents=prompt)
        except genai_errors.ServerError as exc:
            last_error = exc
        except genai_errors.ClientError as exc:
            if getattr(exc, "code", None) != 429:
                raise
            last_error = exc
        if attempt < max_attempts:
            print(f"⚠️ Gemini transport retry {attempt}/{max_attempts}: {last_error}")
            time.sleep(delay)
            delay *= 2
    raise SystemExit(f"Gemini transport failed after {max_attempts} attempts: {last_error}")


def write_attempts(source_timeline: str, attempts: list[dict]) -> Path:
    stamp = Path(source_timeline).stem.replace("narration_timeline_", "")
    path = OUTPUT_DIR / f"storyboard_attempts_{stamp}.json"
    path.write_text(json.dumps(attempts, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def generate_storyboard(timeline: dict, source_timeline: str) -> tuple[dict, bool]:
    if not API_KEY:
        raise SystemExit("GEMINI_API_KEY is not set.")
    fixed_scenes = deterministic_partition(timeline)
    print(f"   Deterministic timing partition: {len(fixed_scenes)} valid scenes")
    for s in fixed_scenes:
        print(f"   T{s['scene_id']:02d} {s['start']:.2f}-{s['end']:.2f}s words {s['start_word']}-{s['end_word']}")

    client = genai.Client(api_key=API_KEY)
    attempts: list[dict] = []
    first = call_gemini(client, build_prompt(fixed_scenes))
    first_text = first.text or ""
    try:
        result = enrich_and_validate(extract_json(first_text), fixed_scenes, timeline, source_timeline)
        attempts.append({"attempt": 1, "status": "accepted", "response": first_text})
        write_attempts(source_timeline, attempts)
        return result, False
    except (json.JSONDecodeError, StoryboardValidationError, KeyError, TypeError, ValueError) as exc:
        error = str(exc)
        attempts.append({"attempt": 1, "status": "rejected", "error": error, "response": first_text})
        print(f"⚠️ Initial semantic metadata rejected: {error}")

    repaired = call_gemini(client, build_repair_prompt(fixed_scenes, first_text, error))
    repaired_text = repaired.text or ""
    try:
        result = enrich_and_validate(extract_json(repaired_text), fixed_scenes, timeline, source_timeline)
        attempts.append({"attempt": 2, "status": "accepted", "response": repaired_text})
        write_attempts(source_timeline, attempts)
        return result, True
    except (json.JSONDecodeError, StoryboardValidationError, KeyError, TypeError, ValueError) as exc:
        error2 = str(exc)
        attempts.append({"attempt": 2, "status": "rejected", "error": error2, "response": repaired_text})
        write_attempts(source_timeline, attempts)
        raise SystemExit("Storyboard failed closed after one semantic repair: " + error2) from exc


def main() -> None:
    timeline_path = find_latest_timeline()
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    timestamp = timeline_path.stem.replace("narration_timeline_", "")
    out = OUTPUT_DIR / f"storyboard_{timestamp}.json"
    print(f"🎞️ Planning storyboard from {timeline_path.name}...")
    storyboard, repaired = generate_storyboard(timeline, timeline_path.name)
    out.write_text(json.dumps(storyboard, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Storyboard saved: {out}")
    print(f"   Scenes: {storyboard['scene_count']} | semantic repair used: {'yes' if repaired else 'no'}")
    for s in storyboard["scenes"]:
        print(f"   S{s['scene_id']:02d} {s['start']:.2f}-{s['end']:.2f}s [{s['purpose']}] {s['visual_intent']}")


if __name__ == "__main__":
    main()
