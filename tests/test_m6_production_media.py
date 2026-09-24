from pathlib import Path
import pytest

from scripts.m6_production_media import ProductionMediaError, resolve_voice_artifact


def _write(path: Path):
    path.write_bytes(b"audio")


def test_resolves_ryan_lossless_wav(tmp_path):
    wav = tmp_path / "voice_123.wav"
    _write(wav)
    assert resolve_voice_artifact(tmp_path, "123") == wav


def test_resolves_edge_rollback_mp3(tmp_path):
    mp3 = tmp_path / "voice_123.mp3"
    _write(mp3)
    assert resolve_voice_artifact(tmp_path, "123") == mp3


def test_fails_closed_on_stale_cross_backend_audio(tmp_path):
    _write(tmp_path / "voice_123.wav")
    _write(tmp_path / "voice_123.mp3")
    with pytest.raises(ProductionMediaError, match="AMBIGUOUS_VOICE_ARTIFACT"):
        resolve_voice_artifact(tmp_path, "123")


def test_fails_closed_when_audio_missing(tmp_path):
    with pytest.raises(ProductionMediaError, match="MISSING_VOICE_ARTIFACT"):
        resolve_voice_artifact(tmp_path, "123")
