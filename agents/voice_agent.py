"""
Step 2: Voice + Narration Timeline Agent
-----------------------------------------
Takes the most recent script JSON and synthesizes narration with Edge-TTS.
The same synthesis pass writes both the MP3 audio and the authoritative
word-boundary timeline used by captions and, later, the storyboard.

Outputs for a script_<timestamp>.json:
    voice_<timestamp>.mp3
    narration_timeline_<timestamp>.json
"""

import asyncio
import json
import sys
from pathlib import Path

import edge_tts

OUTPUT_DIR = Path(__file__).parent / "output"
VOICE = "en-US-GuyNeural"
RATE = "+0%"
TICKS_PER_SECOND = 10_000_000


def find_latest_script() -> Path:
    scripts = sorted(OUTPUT_DIR.glob("script_*.json"))
    if not scripts:
        raise SystemExit(
            "No script_*.json files found in agents/output/. Run script_agent.py first."
        )
    return scripts[-1]


def validate_timeline(timeline: dict) -> None:
    text = timeline.get("text", "")
    words = timeline.get("words", [])
    duration = timeline.get("duration", 0)

    if not text.strip():
        raise ValueError("Narration timeline has empty canonical text.")
    if not words:
        raise ValueError("Edge-TTS returned no WordBoundary events.")
    if duration <= 0:
        raise ValueError("Narration timeline duration must be positive.")

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

    if abs(duration - previous_end) > 0.02:
        raise ValueError(
            f"Timeline duration {duration:.3f}s does not match final boundary {previous_end:.3f}s."
        )


async def generate_voice_and_timeline(text: str, audio_path: Path) -> list[dict]:
    """Synthesize once and capture the exact Edge-TTS WordBoundary events."""
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
                duration = float(chunk["duration"]) / TICKS_PER_SECOND
                boundaries.append(
                    {
                        "index": len(boundaries),
                        "word": str(chunk["text"]),
                        "start": round(start, 4),
                        "end": round(start + duration, 4),
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

    words = asyncio.run(generate_voice_and_timeline(script_text, voice_path))
    duration = words[-1]["end"] if words else 0.0
    timeline = {
        "schema_version": 1,
        "source_script": script_path.name,
        "text": script_text,
        "voice": VOICE,
        "rate": RATE,
        "duration": duration,
        "words": words,
    }
    validate_timeline(timeline)
    timeline_path.write_text(
        json.dumps(timeline, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"✅ Voice saved: {voice_path}")
    print(f"✅ Narration timeline saved: {timeline_path}")
    print(f"   Word boundaries: {len(words)} | timeline duration: {duration:.2f}s")


if __name__ == "__main__":
    if sys.version_info < (3, 8):
        raise SystemExit("Python 3.8+ required.")
    main()
