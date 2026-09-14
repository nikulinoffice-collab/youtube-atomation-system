"""Semantic storyboard planner with strict fail-closed validation.

Gemini selects contiguous canonical word-index ranges. Python, not the model,
derives timestamps from narration_timeline_<timestamp>.json. One semantic repair
pass is allowed; transport retries do not count as semantic repair.
"""

import json
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
    matches = sorted(OUTPUT_DIR.glob("narration_timeline_*.json"))
    if not matches:
        raise SystemExit("No narration_timeline_*.json found. Run voice_agent.py first.")
    return matches[-1]


def extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise StoryboardValidationError("Storyboard response must be one JSON object.")
    return data


def canonical_scene_text(words: list[dict], start_word: int, end_word: int) -> str:
    return "".join(
        str(w.get("separator_before", "")) + str(w["word"])
        for w in words[start_word : end_word + 1]
    ).strip()


def normalize_queries(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise StoryboardValidationError("search_queries must be a JSON array.")
    queries = [str(item).strip() for item in value]
    if not (MIN_QUERIES <= len(queries) <= MAX_QUERIES):
        raise StoryboardValidationError(
            f"Each scene requires {MIN_QUERIES}-{MAX_QUERIES} search queries."
        )
    if any(not q or len(q) < 3 or len(q) > 120 for q in queries):
        raise StoryboardValidationError("Search queries must be non-empty and 3-120 chars.")
    if len({q.casefold() for q in queries}) != len(queries):
        raise StoryboardValidationError("search_queries must be unique within a scene.")
    return queries


def materialize_and_validate(raw: dict, timeline: dict, source_timeline: str) -> dict:
    words = timeline.get("words")
    if not isinstance(words, list) or not words:
        raise StoryboardValidationError("Narration timeline contains no words.")
    raw_scenes = raw.get("scenes")
    if not isinstance(raw_scenes, list):
        raise StoryboardValidationError("Storyboard must contain a scenes array.")
    if not (MIN_SCENES <= len(raw_scenes) <= MAX_SCENES):
        raise StoryboardValidationError(
            f"Storyboard must contain {MIN_SCENES}-{MAX_SCENES} scenes; got {len(raw_scenes)}."
        )

    scenes: list[dict] = []
    expected_start = 0
    for scene_id, raw_scene in enumerate(raw_scenes, start=1):
        if not isinstance(raw_scene, dict):
            raise StoryboardValidationError(f"Scene {scene_id} must be an object.")
        try:
            start_word = int(raw_scene["start_word"])
            end_word = int(raw_scene["end_word"])
        except (KeyError, TypeError, ValueError) as exc:
            raise StoryboardValidationError(
                f"Scene {scene_id} requires integer start_word/end_word."
            ) from exc

        if start_word != expected_start:
            raise StoryboardValidationError(
                f"Scene {scene_id} must start at word {expected_start}, got {start_word}; "
                "gaps and overlaps are forbidden."
            )
        if end_word < start_word or end_word >= len(words):
            raise StoryboardValidationError(
                f"Scene {scene_id} has invalid word range {start_word}..{end_word}."
            )

        start = float(words[start_word]["start"])
        end = float(words[end_word]["end"])
        duration = end - start
        if duration < MIN_SCENE_SECONDS or duration > MAX_SCENE_SECONDS:
            raise StoryboardValidationError(
                f"Scene {scene_id} duration {duration:.3f}s is outside "
                f"{MIN_SCENE_SECONDS:.1f}-{MAX_SCENE_SECONDS:.1f}s. "
                "Merge an undersized scene with an adjacent semantic scene; do not just "
                "move the same short range to another scene."
            )

        purpose = str(raw_scene.get("purpose", "")).strip()
        if purpose not in ALLOWED_PURPOSES:
            raise StoryboardValidationError(f"Scene {scene_id} purpose {purpose!r} is invalid.")
        visual_intent = str(raw_scene.get("visual_intent", "")).strip()
        if len(visual_intent) < 12 or len(visual_intent) > 240:
            raise StoryboardValidationError(
                f"Scene {scene_id} visual_intent must be 12-240 characters."
            )
        if visual_intent.casefold() in {"ai", "artificial intelligence", "technology", "tech"}:
            raise StoryboardValidationError(
                f"Scene {scene_id} visual_intent is too generic: {visual_intent!r}."
            )
        asset_type = str(raw_scene.get("preferred_asset_type", "either")).strip()
        if asset_type not in ALLOWED_ASSET_TYPES:
            raise StoryboardValidationError(
                f"Scene {scene_id} preferred_asset_type {asset_type!r} is invalid."
            )

        scenes.append({
            "scene_id": scene_id,
            "start_word": start_word,
            "end_word": end_word,
            "start": round(start, 4),
            "end": round(end, 4),
            "duration": round(duration, 4),
            "narration": canonical_scene_text(words, start_word, end_word),
            "purpose": purpose,
            "visual_intent": visual_intent,
            "search_queries": normalize_queries(raw_scene.get("search_queries")),
            "preferred_asset_type": asset_type,
        })
        expected_start = end_word + 1

    if expected_start != len(words):
        raise StoryboardValidationError(
            f"Storyboard stops at word {expected_start - 1}; final word is {len(words) - 1}."
        )
    for left, right in zip(scenes, scenes[1:]):
        if right["start_word"] != left["end_word"] + 1:
            raise StoryboardValidationError("Storyboard word coverage is not contiguous.")
        if right["start"] + 1e-6 < left["end"]:
            raise StoryboardValidationError("Storyboard scene timings overlap.")

    return {
        "schema_version": 1,
        "source_timeline": source_timeline,
        "model": MODEL,
        "duration": float(timeline["duration"]),
        "speech_start": float(timeline["speech_start"]),
        "speech_end": float(timeline["speech_end"]),
        "scene_count": len(scenes),
        "scenes": scenes,
    }


def compact_word_map(timeline: dict) -> str:
    return "\n".join(
        f"{w['index']}: {w['word']} [{float(w['start']):.2f}-{float(w['end']):.2f}]"
        for w in timeline["words"]
    )


def build_prompt(timeline: dict) -> str:
    return f"""You are a storyboard planner for a ~30-second vertical AI/tech news Short.

Divide the EXACT narration into 8-12 semantic visual scenes using contiguous word-index
ranges. Prefer 8-10 scenes unless the narration clearly needs more. Python derives all
real timestamps from the selected word indexes; never invent timestamps.

Narration:
{timeline['text']}

Authoritative word map (index: token [start-end seconds]):
{compact_word_map(timeline)}

Hard rules:
- First start_word = 0; each next start_word = previous end_word + 1.
- Final end_word = {len(timeline['words']) - 1}; every word appears exactly once.
- EVERY scene must be 1.2-6.0 seconds by the word-map timestamps; target 2-4 seconds.
- Before returning JSON, calculate every proposed scene duration from the word map.
- NEVER create a micro-scene under 1.2 seconds. If a short payoff/question/fragment
  would be under 1.2 seconds, MERGE it into the previous or next semantic scene.
- Put boundaries at real semantic changes: hook, fact/source, actor/company, claim,
  counterargument, evidence/context, consequence, payoff.
- visual_intent must name a concrete visible subject/action/location, never generic AI.
- Give 2-4 concise Pexels-friendly search queries, specific first then broader fallback.
- preferred_asset_type: video, image, either, or source_card.
- source_card only when narration explicitly discusses the source/article.
- purpose must be one of: {', '.join(sorted(ALLOWED_PURPOSES))}.

Return ONLY JSON:
{{"scenes":[{{"start_word":0,"end_word":7,"purpose":"hook",
"visual_intent":"specific visible subject and action",
"search_queries":["specific query","broader fallback"],
"preferred_asset_type":"video"}}]}}
"""


def build_repair_prompt(timeline: dict, prior_text: str, error: str) -> str:
    return f"""The storyboard below failed a strict validator. You have exactly ONE
semantic repair attempt. Return a COMPLETE corrected JSON object only.

VALIDATION ERROR:
{error}

PREVIOUS RESPONSE:
{prior_text}

Repair strategy is mandatory:
1. Keep complete contiguous coverage of all word indexes.
2. If the error is an undersized (<1.2s) scene, MERGE that whole short semantic beat
   with an adjacent scene and reduce scene_count if needed. Do NOT merely shift the
   too-short range so that a different scene becomes too short.
3. Recalculate every scene duration from the authoritative word-map timestamps before
   returning. Every scene must be 1.2-6.0s and total scene count must stay 8-12.
4. Preserve concrete visual intent and 2-4 unique search queries for every resulting scene.

FULL CONTRACT:
{build_prompt(timeline)}
"""


def call_gemini(client, prompt: str, max_attempts: int = 4):
    delay = 15
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(model=MODEL, contents=prompt)
        except genai_errors.ServerError as exc:
            last_error = exc
            print(f"⚠️  Gemini server error ({attempt}/{max_attempts}): {exc}")
        except genai_errors.ClientError as exc:
            if getattr(exc, "code", None) != 429:
                raise
            last_error = exc
            print(f"⚠️  Gemini rate limited ({attempt}/{max_attempts}): {exc}")
        if attempt < max_attempts:
            time.sleep(delay)
            delay *= 2
    raise SystemExit(f"Gemini transport failed after {max_attempts} attempts: {last_error}")


def write_attempts(source_timeline: str, attempts: list[dict]) -> Path:
    stamp = Path(source_timeline).stem.replace("narration_timeline_", "")
    path = OUTPUT_DIR / f"storyboard_attempts_{stamp}.json"
    path.write_text(json.dumps(attempts, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def generate_valid_storyboard(timeline: dict, source_timeline: str) -> tuple[dict, bool]:
    if not API_KEY:
        raise SystemExit("GEMINI_API_KEY is not set.")
    client = genai.Client(api_key=API_KEY)
    attempts: list[dict] = []

    first = call_gemini(client, build_prompt(timeline))
    first_text = first.text or ""
    try:
        result = materialize_and_validate(extract_json(first_text), timeline, source_timeline)
        attempts.append({"attempt": 1, "status": "accepted", "response": first_text})
        write_attempts(source_timeline, attempts)
        return result, False
    except (json.JSONDecodeError, StoryboardValidationError, KeyError, TypeError, ValueError) as exc:
        error = str(exc)
        attempts.append({"attempt": 1, "status": "rejected", "error": error, "response": first_text})
        print(f"⚠️  Initial storyboard rejected: {error}")
        print("   Attempting one semantic repair pass...")

    repaired = call_gemini(client, build_repair_prompt(timeline, first_text, error))
    repaired_text = repaired.text or ""
    try:
        result = materialize_and_validate(extract_json(repaired_text), timeline, source_timeline)
        attempts.append({"attempt": 2, "status": "accepted", "response": repaired_text})
        write_attempts(source_timeline, attempts)
        return result, True
    except (json.JSONDecodeError, StoryboardValidationError, KeyError, TypeError, ValueError) as exc:
        repair_error = str(exc)
        attempts.append({"attempt": 2, "status": "rejected", "error": repair_error, "response": repaired_text})
        write_attempts(source_timeline, attempts)
        raise SystemExit("Storyboard failed closed after one repair pass: " + repair_error) from exc


def main() -> None:
    timeline_path = find_latest_timeline()
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    timestamp = timeline_path.stem.replace("narration_timeline_", "")
    out = OUTPUT_DIR / f"storyboard_{timestamp}.json"

    print(f"🎞️  Planning semantic storyboard from {timeline_path.name}...")
    storyboard, repaired = generate_valid_storyboard(timeline, timeline_path.name)
    out.write_text(json.dumps(storyboard, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Storyboard saved: {out}")
    print(
        f"   Scenes: {storyboard['scene_count']} | speech: "
        f"{storyboard['speech_start']:.2f}-{storyboard['speech_end']:.2f}s | "
        f"semantic repair used: {'yes' if repaired else 'no'}"
    )
    for scene in storyboard["scenes"]:
        print(
            f"   S{scene['scene_id']:02d} {scene['start']:.2f}-{scene['end']:.2f}s "
            f"[{scene['purpose']}] {scene['visual_intent']}"
        )


if __name__ == "__main__":
    main()
