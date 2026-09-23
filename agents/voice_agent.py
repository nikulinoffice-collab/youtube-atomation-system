"""
Step 2: Voice + Narration Timeline Agent
-----------------------------------------
Takes the most recent script JSON and synthesizes narration with Edge-TTS.
The same synthesis pass writes both the MP3 audio and the authoritative
word-boundary timeline used by captions and storyboard.

Canonical text remains the source of truth. Edge-TTS may split punctuation-
joined text (for example ``think—should``) or keep compounds such as
``billion-dollar`` as one WordBoundary. Alignment therefore operates on
lexical spans and can merge adjacent canonical lexical tokens into one TTS
boundary while preserving exact source punctuation and spacing.

Outputs for a script_<timestamp>.json:
    voice_<timestamp>.mp3
    narration_timeline_<timestamp>.json
"""

import asyncio
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


OUTPUT_DIR = Path(__file__).parent / "output"
VOICE = "en-US-GuyNeural"  # rollback voice; M6.9 Ryan path is selected explicitly
RATE = "+0%"
VOICE_BACKEND = "edge"
TICKS_PER_SECOND = 10_000_000
MAX_TRAILING_AUDIO_SECONDS = 1.5
LEXICAL_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)


def find_latest_script() -> Path:
    scripts = sorted(OUTPUT_DIR.glob("script_*.json"))
    if not scripts:
        raise SystemExit(
            "No script_*.json files found in agents/output/. Run script_agent.py first."
        )
    return scripts[-1]


def lexical_form(token: str) -> str:
    normalized = unicodedata.normalize("NFKC", token).casefold()
    return "".join(ch for ch in normalized if ch.isalnum())


def canonical_lexical_tokens(text: str) -> list[dict]:
    """Split canonical text into lexical units without losing formatting."""
    matches = list(LEXICAL_RE.finditer(text))
    if not matches:
        return []

    tokens: list[dict] = []
    pending_prefix = text[: matches[0].start()]
    for index, match in enumerate(matches):
        core = match.group(0)
        if index + 1 < len(matches):
            between = text[match.end() : matches[index + 1].start()]
            whitespace = re.search(r"\s", between)
            if whitespace:
                split_at = whitespace.start()
                suffix = between[:split_at]
                next_prefix = between[split_at:]
            else:
                suffix = between
                next_prefix = ""
        else:
            suffix = text[match.end() :]
            next_prefix = ""

        tokens.append(
            {
                "separator_before": pending_prefix,
                "word": core + suffix,
                "lexical_core": core,
            }
        )
        pending_prefix = next_prefix

    reconstructed = "".join(t["separator_before"] + t["word"] for t in tokens)
    if reconstructed != text:
        raise ValueError("Canonical lexical tokenizer did not preserve source text exactly.")
    return tokens


def merge_canonical_group(group: list[dict]) -> tuple[str, str]:
    """Return exact separator/word text for canonical tokens mapped to one boundary."""
    if not group:
        raise ValueError("Cannot merge an empty canonical token group.")
    separator = str(group[0]["separator_before"])
    word = str(group[0]["word"])
    for token in group[1:]:
        word += str(token["separator_before"]) + str(token["word"])
    return separator, word


def attach_canonical_tokens(text: str, boundaries: list[dict]) -> list[dict]:
    """Keep Edge timings while restoring exact canonical punctuation/spacing.

    Edge sometimes emits a single boundary for a punctuation compound that our
    canonical lexical tokenizer represents as multiple lexical cores. We align
    sequentially by accumulating canonical cores until their normalized lexical
    form equals the current TTS boundary. This is strict and fail-closed: every
    canonical core and every boundary must be consumed exactly once.
    """
    canonical_tokens = canonical_lexical_tokens(text)
    if not canonical_tokens:
        raise ValueError("Canonical narration contains no lexical tokens.")
    if not boundaries:
        raise ValueError("Edge-TTS returned no WordBoundary events.")

    aligned: list[dict] = []
    canonical_index = 0
    for boundary_index, boundary in enumerate(boundaries):
        boundary_lex = lexical_form(str(boundary["boundary_text"]))
        if not boundary_lex:
            raise ValueError(f"TTS boundary {boundary_index} has no lexical content.")
        if canonical_index >= len(canonical_tokens):
            raise ValueError(
                f"TTS returned extra boundary {boundary_index}: {boundary['boundary_text']!r}"
            )

        group: list[dict] = []
        combined = ""
        while canonical_index < len(canonical_tokens):
            token = canonical_tokens[canonical_index]
            token_lex = lexical_form(str(token["lexical_core"]))
            if not token_lex:
                raise ValueError(f"Canonical token {canonical_index} has no lexical content.")
            candidate = combined + token_lex
            if not boundary_lex.startswith(candidate):
                raise ValueError(
                    f"Narration lexical mismatch at TTS boundary {boundary_index}: "
                    f"canonical_prefix={candidate!r}, tts={boundary_lex!r}, "
                    f"boundary_text={boundary['boundary_text']!r}"
                )
            group.append(token)
            combined = candidate
            canonical_index += 1
            if combined == boundary_lex:
                break

        if combined != boundary_lex:
            raise ValueError(
                f"Canonical narration could not fully match TTS boundary {boundary_index}: "
                f"canonical={combined!r}, tts={boundary_lex!r}"
            )

        separator, word = merge_canonical_group(group)
        aligned.append(
            {
                "index": boundary_index,
                "separator_before": separator,
                "word": word,
                "start": boundary["start"],
                "end": boundary["end"],
            }
        )

    if canonical_index != len(canonical_tokens):
        remaining = canonical_tokens[canonical_index: canonical_index + 3]
        raise ValueError(
            "Canonical narration has lexical tokens with no TTS boundary after alignment: "
            + repr([token["lexical_core"] for token in remaining])
        )

    return aligned


def reconstruct_text(words: list[dict]) -> str:
    return "".join(str(word.get("separator_before", "")) + str(word["word"]) for word in words)


def get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"ffprobe failed for narration audio: {result.stderr.strip()}")
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise ValueError("ffprobe returned an invalid narration duration.") from exc
    if duration <= 0:
        raise ValueError("Narration audio duration must be positive.")
    return duration


def validate_timeline(timeline: dict) -> None:
    text = timeline.get("text", "")
    words = timeline.get("words", [])
    duration = float(timeline.get("duration", 0))
    speech_end = float(timeline.get("speech_end", 0))

    if not text.strip():
        raise ValueError("Narration timeline has empty canonical text.")
    if not words:
        raise ValueError("Edge-TTS returned no WordBoundary events.")
    if duration <= 0 or speech_end <= 0:
        raise ValueError("Narration timeline durations must be positive.")

    previous_start = -1.0
    previous_end = 0.0
    for expected_index, word in enumerate(words):
        if word.get("index") != expected_index:
            raise ValueError("Narration word indexes are not contiguous.")
        if not str(word.get("word", "")).strip():
            raise ValueError(f"Narration word {expected_index} is empty.")
        start = float(word["start"])
        end = float(word["end"])
        if start < 0 or end <= start:
            raise ValueError(f"Invalid timing for narration word {expected_index}: {start}..{end}")
        if start < previous_start:
            raise ValueError("Narration word starts are not monotonic.")
        if start + 1e-6 < previous_end:
            raise ValueError(
                f"Overlapping narration boundaries at word {expected_index}: "
                f"previous_end={previous_end}, start={start}"
            )
        previous_start = start
        previous_end = end

    if abs(speech_end - previous_end) > 0.02:
        raise ValueError("speech_end does not match the final word boundary.")
    if duration + 0.02 < speech_end:
        raise ValueError("Narration audio ends before the final word boundary.")
    if duration - speech_end > MAX_TRAILING_AUDIO_SECONDS:
        raise ValueError(
            f"Narration audio has excessive trailing time: {duration - speech_end:.3f}s"
        )
    if reconstruct_text(words) != text:
        raise ValueError("Timeline lexical units no longer reconstruct canonical narration exactly.")


def selected_backend() -> str:
    import os
    backend = os.environ.get("FACTORY_VOICE_BACKEND", VOICE_BACKEND).strip().lower()
    if backend not in {"edge", "m6-ryan"}:
        raise ValueError(f"Unsupported FACTORY_VOICE_BACKEND: {backend}")
    return backend


async def generate_voice_and_boundaries(text: str, audio_path: Path) -> list[dict]:
    import edge_tts  # lazy rollback-only dependency; Ryan path must not require Edge-TTS\n    communicate = edge_tts.Communicate(text, voice=VOICE, rate=RATE, boundary="WordBoundary")
    boundaries: list[dict] = []
    with audio_path.open("wb") as audio_file:
        async for chunk in communicate.stream():
            chunk_type = chunk.get("type")
            if chunk_type == "audio":
                audio_file.write(chunk["data"])
            elif chunk_type == "WordBoundary":
                start = float(chunk["offset"]) / TICKS_PER_SECOND
                boundary_duration = float(chunk["duration"]) / TICKS_PER_SECOND
                boundaries.append(
                    {
                        "boundary_text": str(chunk["text"]),
                        "start": round(start, 4),
                        "end": round(start + boundary_duration, 4),
                    }
                )
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise ValueError("Edge-TTS produced no audio bytes.")
    return boundaries


def main():
    script_path = find_latest_script()
    data = json.loads(script_path.read_text(encoding="utf-8"))
    script_text = str(data["script"]).strip()
    if not script_text:
        raise SystemExit("Latest script contains an empty 'script' field.")

    timestamp = script_path.stem.replace("script_", "")
    voice_path = OUTPUT_DIR / f"voice_{timestamp}.mp3"
    timeline_path = OUTPUT_DIR / f"narration_timeline_{timestamp}.json"

    backend = selected_backend()
    print(f"🗣️  Generating voice for: {data['title']}")
    print(f"   Backend: {backend}")

    if backend == "m6-ryan":
        from scripts.m6_production_ryan import synthesize
        result = synthesize(script_text, voice_path.with_suffix(".wav"))
        from scripts.m6_production_alignment import align
        alignment_path = OUTPUT_DIR / f"m6_alignment_{timestamp}.json"
        aligned = align(voice_path.with_suffix(".wav"), result["voice_plan"], device="cpu")
        alignment_path.write_text(json.dumps(aligned, indent=2, ensure_ascii=False), encoding="utf-8")
        from scripts.m6_production_timeline import build_production_timeline
        timeline = build_production_timeline(
            script_text, aligned["word_timings"], result["duration_s"], voice="Ryan"
        )
        timeline_path.write_text(json.dumps(timeline, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✅ Ryan WAV saved: {voice_path.with_suffix('.wav')}")
        print(f"✅ Narration timeline saved: {timeline_path}")
        return

    print(f"   Voice: {VOICE}  |  Rate: {RATE}")
    boundaries = asyncio.run(generate_voice_and_boundaries(script_text, voice_path))
    words = attach_canonical_tokens(script_text, boundaries)
    speech_end = words[-1]["end"] if words else 0.0
    audio_duration = round(get_audio_duration(voice_path), 4)

    timeline = {
        "schema_version": 2,
        "source_script": script_path.name,
        "text": script_text,
        "voice": VOICE,
        "rate": RATE,
        "duration": audio_duration,
        "speech_start": words[0]["start"] if words else 0.0,
        "speech_end": speech_end,
        "words": words,
    }
    validate_timeline(timeline)
    timeline_path.write_text(json.dumps(timeline, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Voice saved: {voice_path}")
    print(f"✅ Narration timeline saved: {timeline_path}")
    print(
        f"   Canonical/TTS aligned words: {len(words)} | speech end: {speech_end:.2f}s | "
        f"audio duration: {audio_duration:.2f}s"
    )


if __name__ == "__main__":
    if sys.version_info < (3, 8):
        raise SystemExit("Python 3.8+ required.")
    main()
