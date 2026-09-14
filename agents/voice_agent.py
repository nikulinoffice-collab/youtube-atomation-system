"""
Step 2: Voice + Narration Timeline Agent
-----------------------------------------
Takes the most recent script JSON and synthesizes narration with Edge-TTS.
The same synthesis pass writes both the MP3 audio and the authoritative
word-boundary timeline used by captions and storyboard.

Canonical text remains the source of truth. Edge-TTS may split punctuation-
joined text (for example ``think—should`` or ``30-second``) into multiple word
boundaries, so alignment is performed against lexical spans rather than plain
whitespace tokens. Exact original punctuation/spacing is preserved through
``separator_before`` + ``word`` fields.

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

import edge_tts

OUTPUT_DIR = Path(__file__).parent / "output"
VOICE = "en-US-GuyNeural"
RATE = "+0%"
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
    """Split canonical text into spoken lexical units without losing formatting.

    ``word`` owns punctuation immediately following its lexical core until the
    first whitespace before the next core. ``separator_before`` owns initial or
    inter-word whitespace plus any opening punctuation after that whitespace.
    Concatenating separator_before + word for every token reproduces ``text``
    byte-for-byte.
    """
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


def attach_canonical_tokens(text: str, boundaries: list[dict]) -> list[dict]:
    """Keep Edge timings while restoring exact canonical punctuation/spacing."""
    canonical_tokens = canonical_lexical_tokens(text)
    if len(canonical_tokens) != len(boundaries):
        raise ValueError(
            "Canonical narration lexical token count does not match Edge-TTS boundaries: "
            f"script={len(canonical_tokens)}, boundaries={len(boundaries)}"
        )

    aligned: list[dict] = []
    for index, (canonical, boundary) in enumerate(zip(canonical_tokens, boundaries)):
        canonical_lex = lexical_form(canonical["lexical_core"])
        boundary_lex = lexical_form(str(boundary["boundary_text"]))
        if not canonical_lex or canonical_lex != boundary_lex:
            raise ValueError(
                f"Narration lexical mismatch at {index}: canonical={canonical['lexical_core']!r}, "
                f"tts={boundary['boundary_text']!r}"
            )
        aligned.append(
            {
                "index": index,
                "separator_before": canonical["separator_before"],
                "word": canonical["word"],
                "start": boundary["start"],
                "end": boundary["end"],
            }
        )
    return aligned


def reconstruct_text(words: list[dict]) -> str:
    return "".join(str(word.get("separator_before", "")) + str(word["word"]) for word in words)


def get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
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


async def generate_voice_and_boundaries(text: str, audio_path: Path) -> list[dict]:
    """Synthesize once and capture Edge-TTS WordBoundary timings."""
    communicate = edge_tts.Communicate(
        text, voice=VOICE, rate=RATE, boundary="WordBoundary"
    )
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

    print(f"🗣️  Generating voice for: {data['title']}")
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
    timeline_path.write_text(
        json.dumps(timeline, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"✅ Voice saved: {voice_path}")
    print(f"✅ Narration timeline saved: {timeline_path}")
    print(
        f"   Canonical lexical words: {len(words)} | speech end: {speech_end:.2f}s | "
        f"audio duration: {audio_duration:.2f}s"
    )


if __name__ == "__main__":
    if sys.version_info < (3, 8):
        raise SystemExit("Python 3.8+ required.")
    main()
