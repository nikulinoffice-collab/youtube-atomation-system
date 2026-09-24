"""Production narration artifact resolution for M6.9.

Ryan produces lossless WAV; Edge remains the explicit MP3 rollback route.  The
resolver is deliberately fail-closed when both formats exist so downstream
render/QC cannot silently select stale audio from another backend.
"""
from pathlib import Path


class ProductionMediaError(RuntimeError):
    pass


def resolve_voice_artifact(output_dir: Path, timestamp: str) -> Path:
    wav = output_dir / f"voice_{timestamp}.wav"
    mp3 = output_dir / f"voice_{timestamp}.mp3"
    present = [p for p in (wav, mp3) if p.exists() and p.stat().st_size > 0]
    if len(present) == 1:
        return present[0]
    if len(present) > 1:
        raise ProductionMediaError(
            f"AMBIGUOUS_VOICE_ARTIFACT: both {wav.name} and {mp3.name} exist"
        )
    raise ProductionMediaError(
        f"MISSING_VOICE_ARTIFACT: expected exactly one of {wav.name} or {mp3.name}"
    )
