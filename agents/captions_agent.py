"""
Step 4: Caption Composer
------------------------
Builds readable SRT captions directly from the authoritative Edge-TTS
narration timeline. There is no speech-to-text step: captions use the same
canonical words and timings that produced the voice audio.
"""

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
MIN_WORDS = 2
MAX_WORDS = 6
MAX_CHARS = 42
PAUSE_BREAK_SECONDS = 0.45
TERMINAL_PUNCTUATION = (".", "?", "!")


def find_latest_timeline() -> Path:
    files = sorted(OUTPUT_DIR.glob("narration_timeline_*.json"))
    if not files:
        raise SystemExit(
            "No narration_timeline_*.json found in agents/output/. Run voice_agent.py first."
        )
    return files[-1]


def format_srt_timestamp(seconds: float) -> str:
    ms_total = round(seconds * 1000)
    hours, ms_total = divmod(ms_total, 3_600_000)
    minutes, ms_total = divmod(ms_total, 60_000)
    secs, ms = divmod(ms_total, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def should_break(chunk: list[dict], next_word: dict | None) -> bool:
    if not chunk:
        return False
    if len(chunk) >= MAX_WORDS:
        return True
    if next_word is None:
        return True

    last_token = str(chunk[-1]["word"]).rstrip()
    if last_token.endswith(TERMINAL_PUNCTUATION):
        return True
    if len(chunk) < MIN_WORDS:
        return False

    text = " ".join(w["word"].strip() for w in chunk)
    if len(text) >= MAX_CHARS:
        return True
    gap = float(next_word["start"]) - float(chunk[-1]["end"])
    return gap >= PAUSE_BREAK_SECONDS


def compose_cues(words: list[dict]) -> list[dict]:
    cues: list[dict] = []
    chunk: list[dict] = []

    for index, word in enumerate(words):
        chunk.append(word)
        next_word = words[index + 1] if index + 1 < len(words) else None
        if should_break(chunk, next_word):
            cues.append(
                {
                    "text": " ".join(w["word"].strip() for w in chunk),
                    "start": float(chunk[0]["start"]),
                    "end": float(chunk[-1]["end"]),
                    "word_start_index": int(chunk[0]["index"]),
                    "word_end_index": int(chunk[-1]["index"]),
                }
            )
            chunk = []

    if chunk:
        cues.append(
            {
                "text": " ".join(w["word"].strip() for w in chunk),
                "start": float(chunk[0]["start"]),
                "end": float(chunk[-1]["end"]),
                "word_start_index": int(chunk[0]["index"]),
                "word_end_index": int(chunk[-1]["index"]),
            }
        )
    return cues


def wrap_two_lines(text: str) -> str:
    """Balance long cues over at most two lines without changing words."""
    if len(text) <= 24:
        return text
    words = text.split()
    if len(words) <= 2:
        return text

    best_index = min(
        range(1, len(words)),
        key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))),
    )
    return " ".join(words[:best_index]) + "\n" + " ".join(words[best_index:])


def validate_cues(cues: list[dict], words: list[dict], timeline_duration: float) -> None:
    if not cues:
        raise ValueError("Caption composer produced no cues.")

    flattened = []
    previous_end = 0.0
    for cue in cues:
        start = float(cue["start"])
        end = float(cue["end"])
        if start < previous_end - 1e-6:
            raise ValueError("Caption cues overlap.")
        if end <= start:
            raise ValueError("Caption cue has non-positive duration.")
        if end > timeline_duration + 0.02:
            raise ValueError("Caption cue extends beyond narration timeline.")
        flattened.extend(range(cue["word_start_index"], cue["word_end_index"] + 1))
        previous_end = end

    if flattened != list(range(len(words))):
        raise ValueError("Caption cues do not cover every narration word exactly once.")

    source_text = " ".join(word["word"] for word in words)
    cue_text = " ".join(cue["text"] for cue in cues)
    if cue_text != source_text:
        raise ValueError("Caption text differs from canonical narration.")


def write_srt(cues: list[dict], out_path: Path) -> None:
    blocks = []
    for idx, cue in enumerate(cues, start=1):
        blocks.append(
            f"{idx}\n"
            f"{format_srt_timestamp(cue['start'])} --> {format_srt_timestamp(cue['end'])}\n"
            f"{wrap_two_lines(cue['text'])}\n"
        )
    out_path.write_text("\n".join(blocks), encoding="utf-8")


def main():
    timeline_path = find_latest_timeline()
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    words = timeline.get("words", [])
    duration = float(timeline.get("duration", 0))
    if not words or duration <= 0:
        raise SystemExit("Narration timeline is empty or invalid.")

    timestamp = timeline_path.stem.replace("narration_timeline_", "")
    cues = compose_cues(words)
    validate_cues(cues, words, duration)

    srt_path = OUTPUT_DIR / f"captions_{timestamp}.srt"
    cues_path = OUTPUT_DIR / f"caption_cues_{timestamp}.json"
    write_srt(cues, srt_path)
    cues_path.write_text(json.dumps(cues, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Captions saved: {srt_path}")
    print(f"✅ Caption cue manifest saved: {cues_path}")
    print(f"   {len(words)} authoritative words grouped into {len(cues)} cues")


if __name__ == "__main__":
    main()
