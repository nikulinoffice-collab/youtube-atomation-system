"""
Step 4: Storyboard Agent
------------------------
Builds a semantic visual storyboard from the canonical narration timeline.
Gemini chooses contiguous WORD INDEX ranges; Python derives exact scene times
from narration_timeline_<timestamp>.json and validates the complete contract.

The model never controls FFmpeg timestamps directly.

Output:
    storyboard_<timestamp>.json

Fail-closed policy:
- Initial model response is parsed and validated.
- If invalid, exactly ONE semantic repair pass is allowed.
- If the repaired response is still invalid, the agent exits non-zero.
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
    "hook",
    "source",
    "fact",
    "context",
    "person_company",
    "claim",
    "counterargument",
    "evidence",
    "consequence",
    "payoff",
    "transition",
}
ALLOWED_ASSET_TYPES = {"video", "image", "either", "source_card"}


class StoryboardValidationError(ValueError):
    """Raised when the storyboard contract is malformed or unsafe."""


def find_latest_timeline() -> Path:
    matches = sorted(OUTPUT_DIR.glob("narration_timeline_*.json"))
    if not matches:
        raise SystemExit(
            "No narration_timeline_*.json found. Run voice_agent.py first."
        )
    return matches[-1]


def extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise StoryboardValidationError("Storyboard response must be one JSON object.")
    return data


def canonical_scene_text(words: list[dict], start_word: int, end_word: int) -> str:
    selected = words[start_word : end_word + 1]
    return "".join(
        str(word.get("separator_before", "")) + str(word["word"])
        for word in selected
    ).strip()


def normalize_queries(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise StoryboardValidationError("search_queries must be a JSON array.")
    queries = [str(item).strip() for item in value]
    if any(not item for item in queries):
        raise StoryboardValidationError("search_queries may not contain empty values.")
    if not (MIN_QUERIES <= len(queries) <= MAX_QUERIES):
        raise StoryboardValidationError(
            f"Each scene requires {MIN_QUERIES}-{MAX_QUERIES} search queries."
        )
    lowered = [query.casefold() for query in queries]
    if len(set(lowered)) != len(lowered):
        raise StoryboardValidationError("search_queries must be unique within a scene.")
    if any(len(query) < 3 or len(query) > 120 for query in queries):
        raise StoryboardValidationError("search query length must be 3-120 characters.")
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

    materialized: list[dict] = []
    expected_start = 0
    for scene_index, raw_scene in enumerate(raw_scenes, start=1):
        if not isinstance(raw_scene, dict):
            raise StoryboardValidationError(f"Scene {scene_index} must be an object.")

        try:
            start_word = int(raw_scene["start_word"])
            end_word = int(raw_scene["end_word"])
        except (KeyError, TypeError, ValueError) as exc:
            raise StoryboardValidationError(
                f"Scene {scene_index} requires integer start_word/end_word."
            ) from exc

        if start_word != expected_start:
            raise StoryboardValidationError(
                f"Scene {scene_index} must start at word {expected_start}, got {start_word}; "
                "gaps and overlaps are forbidden."
            )
        if end_word < start_word or end_word >= len(words):
            raise StoryboardValidationError(
                f"Scene {scene_index} has invalid word range {start_word}..{end_word}."
            )

        start = float(words[start_word]["start"])
        end = float(words[end_word]["end"])
        duration = end - start
        if duration < MIN_SCENE_SECONDS or duration > MAX_SCENE_SECONDS:
            raise StoryboardValidationError(
                f"Scene {scene_index} duration {duration:.3f}s is outside "
                f"{MIN_SCENE_SECONDS:.1f}-{MAX_SCENE_SECONDS:.1f}s."
            )

        purpose = str(raw_scene.get("purpose", "")).strip()
        if purpose not in ALLOWED_PURPOSES:
            raise StoryboardValidationError(
                f"Scene {scene_index} purpose {purpose!r} is not allowed."
            )

        visual_intent = str(raw_scene.get("visual_intent", "")).strip()
        if len(visual_intent) < 12 or len(visual_intent) > 240:
            raise StoryboardValidationError(
                f"Scene {scene_index} visual_intent must be 12-240 characters."
            )
        if visual_intent.casefold() in {"ai", "artificial intelligence", "technology", "tech"}:
            raise StoryboardValidationError(
                f"Scene {scene_index} visual_intent is too generic: {visual_intent!r}."
            )

        preferred_asset_type = str(raw_scene.get("preferred_asset_type", "either")).strip()
        if preferred_asset_type not in ALLOWED_ASSET_TYPES:
            raise StoryboardValidationError(
                f"Scene {scene_index} preferred_asset_type {preferred_asset_type!r} is invalid."
            )

        queries = normalize_queries(raw_scene.get("search_queries"))
        narration = canonical_scene_text(words, start_word, end_word)
        materialized.append(
            {
                "scene_id": scene_index,
                "start_word": start_word,
                "end_word": end_word,
                "start": round(start, 4),
                "end": round(end, 4),
                "duration": round(duration, 4),
                "narration": narration,
                "purpose": purpose,
                "visual_intent": visual_intent,
                "search_queries": queries,
                "preferred_asset_type": preferred_asset_type,
            }
        )
        expected_start = end_word + 1

    if expected_start != len(words):
        raise StoryboardValidationError(
            f"Storyboard stops at word {expected_start - 1}; final word is {len(words) - 1}."
        )

    for previous, current in zip(materialized, materialized[1:]):
        if current["start_word"] != previous["end_word"] + 1:
            raise StoryboardValidationError("Storyboard word coverage is not contiguous.")
        if current["start"] + 1e-6 < previous["end"]:
            raise StoryboardValidationError("Storyboard scene timings overlap.")

    return {
        "schema_version": 1,
        "source_timeline": source_timeline,
        "model": MODEL,
        "duration": float(timeline["duration"]),
        "speech_start": float(timeline["speech_start"]),
        "speech_end": float(timeline["speech_end"]),
        "scene_count": len(materialized),
        "scenes": materialized,
    }


def compact_word_map(timeline: dict) -> str:
    return "\n".join(
        f"{word['index']}: {word['word']} [{float(word['start']):.2f}-{float(word['end']):.2f}]"
        for word in timeline["words"]
    )


def build_prompt(timeline: dict) -> str:
    return f"""You are a storyboard planner for a 30-second vertical AI/tech news Short.

Your job is ONLY to divide the exact narration below into 8-12 semantic visual scenes.
Do not rewrite, omit, or add narration. Select contiguous word-index ranges that cover
EVERY word exactly once. Python will derive all timestamps from those word indexes.

Narration:
{timeline['text']}

Authoritative word map:
{compact_word_map(timeline)}

Storyboard rules:
- Return 8-12 scenes in chronological order.
- Scene 1 start_word MUST be 0.
- Every next start_word MUST equal previous end_word + 1.
- Final scene end_word MUST be {len(timeline['words']) - 1}.
- Aim for roughly 2-4 seconds per scene; hard validator allows 1.2-6.0 seconds.
- Put semantic changes at scene boundaries: hook, source/fact, actor/company, claim,
  counterargument, evidence/context, consequence, payoff.
- visual_intent must describe a concrete visible subject/action/location, not generic "AI".
- Provide 2-4 concise Pexels-friendly search queries, from specific to broader fallback.
- preferred_asset_type must be one of: video, image, either, source_card.
- Use source_card only when the narration is explicitly discussing the source/article.
- purpose must be one of: {', '.join(sorted(ALLOWED_PURPOSES))}.

Return ONLY valid JSON with exactly this top-level shape:
{{
  "scenes": [
    {{
      "start_word": 0,
      "end_word": 7,
      "purpose": "hook",
      "visual_intent": "specific visible subject and action",
      "search_queries": ["specific query", "broader fallback"],
      "preferred_asset_type": "video"
    }}
  ]
}}
"""


def build_repair_prompt(timeline: dict, prior_text: str, error: str) -> str:
    return f"""Your previous storyboard JSON failed a strict validator.
You get exactly one repair attempt. Return a COMPLETE corrected storyboard JSON only.

Validation error:
{error}

Previous response:
{prior_text}

Rebuild it under these non-negotiable constraints:
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


def generate_valid_storyboard(timeline: dict, source_timeline: str) -> tuple[dict, bool]:
    if not API_KEY:
        raise SystemExit("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=API_KEY)
    first = call_gemini(client, build_prompt(timeline))
    first_text = first.text or ""
    try:
        raw = extract_json(first_text)
        return materialize_and_validate(raw, timeline, source_timeline), False
    except (json.JSONDecodeError, StoryboardValidationError, KeyError, TypeError, ValueError) as exc:
        print(f"⚠️  Initial storyboard rejected: {exc}")
        print("   Attempting one semantic repair pass...")
        repaired = call_gemini(client, build_repair_prompt(timeline, first_text, str(exc)))
        repaired_text = repaired.text or ""
        try:
            raw = extract_json(repaired_text)
            return materialize_and_validate(raw, timeline, source_timeline), True
        except (json.JSONDecodeError, StoryboardValidationError, KeyError, TypeError, ValueError) as repair_exc:
            raise SystemExit(
                "Storyboard failed closed after one repair pass: " + str(repair_exc)
            ) from repair_exc


def main() -> None:
    timeline_path = find_latest_timeline()
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    timestamp = timeline_path.stem.replace("narration_timeline_", "")
    output_path = OUTPUT_DIR / f"storyboard_{timestamp}.json"

    print(f"🎞️  Planning semantic storyboard from {timeline_path.name}...")
    storyboard, repaired = generate_valid_storyboard(timeline, timeline_path.name)
    output_path.write_text(
        json.dumps(storyboard, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"✅ Storyboard saved: {output_path}")
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
