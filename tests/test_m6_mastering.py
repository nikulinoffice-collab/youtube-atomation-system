import hashlib
import json
import math
import shutil
import struct
import wave
from pathlib import Path

import pytest

from scripts.m6_mastering import MasteringError, inspect_pcm16_wav, master_wav, validate_source


def write_wav(path: Path, *, seconds=0.25, rate=24000, amplitude=4000, silence=False):
    frames = int(seconds * rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        samples = []
        for i in range(frames):
            value = 0 if silence else int(amplitude * math.sin(2 * math.pi * 440 * i / rate))
            samples.append(struct.pack("<h", value))
        w.writeframes(b"".join(samples))


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_inspection_and_source_policy(tmp_path):
    src = tmp_path / "source.wav"
    write_wav(src)
    stats = inspect_pcm16_wav(src)
    assert stats.sample_rate == 24000
    assert stats.channels == 1
    assert stats.duration_s == pytest.approx(0.25)
    assert 0 < stats.peak_fraction < 0.9999
    validate_source(stats)


def test_rejects_pathological_silence(tmp_path):
    src = tmp_path / "silent.wav"
    write_wav(src, silence=True)
    with pytest.raises(MasteringError, match="pathological_silence_resynthesize"):
        validate_source(inspect_pcm16_wav(src))


def test_rejects_clipped_source(tmp_path):
    src = tmp_path / "clipped.wav"
    with wave.open(str(src), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
        w.writeframes(struct.pack("<h", 32767) * 2400)
    with pytest.raises(MasteringError, match="source_clipping_detected_resynthesize"):
        validate_source(inspect_pcm16_wav(src))


def test_refuses_overwrite_of_unmastered_source(tmp_path):
    src = tmp_path / "source.wav"
    write_wav(src)
    with pytest.raises(MasteringError, match="unmastered_source_must_be_preserved"):
        master_wav(src, src, tmp_path / "manifest.json")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required")
def test_mastering_preserves_source_and_records_exact_provenance(tmp_path):
    src = tmp_path / "unmastered.wav"
    out = tmp_path / "mastered.wav"
    manifest = tmp_path / "mastering.json"
    write_wav(src, seconds=0.5)
    original = sha(src)
    record = master_wav(src, out, manifest)
    assert src.exists() and sha(src) == original
    assert out.exists() and manifest.exists()
    persisted = json.loads(manifest.read_text())
    assert persisted == record
    assert record["schema_version"] == "m6.mastering.v1"
    assert record["policy"] == "restrained_technical_only"
    assert record["poor_tts_action"] == "resynthesize_not_dsp"
    assert record["source"]["sha256"] == original
    assert record["mastered"]["sha256"] == sha(out)
    assert record["filter"] == "loudnorm=I=-16:LRA=11:TP=-1.5"
    assert record["ffmpeg_command"][0] == "ffmpeg"
    assert record["ffmpeg_version"].startswith("ffmpeg version")
    assert record["mastered"]["stats"]["duration_s"] == pytest.approx(record["source"]["stats"]["duration_s"], abs=0.02)
