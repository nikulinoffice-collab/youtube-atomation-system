from pathlib import Path

import pytest

from scripts.m6_production_media import ProductionMediaError
from scripts.m6_production_package_gate import verify_production_package


def _package(root: Path, ts: str, voice_ext: str) -> None:
    (root / f"voice_{ts}.{voice_ext}").write_bytes(b"voice")
    for name, ext in (
        ("qc_report", "json"),
        ("renderer_manifest", "json"),
        ("narration_timeline", "json"),
        ("storyboard", "json"),
        ("asset_manifest", "json"),
        ("candidate_manifest", "json"),
        ("captions", "srt"),
        ("final", "mp4"),
    ):
        (root / f"{name}_{ts}.{ext}").write_bytes(b"x")


def test_package_gate_accepts_ryan_lossless_wav(tmp_path: Path):
    _package(tmp_path, "42", "wav")
    assert verify_production_package(tmp_path, "42").name == "voice_42.wav"


def test_package_gate_accepts_explicit_edge_rollback_mp3(tmp_path: Path):
    _package(tmp_path, "42", "mp3")
    assert verify_production_package(tmp_path, "42").name == "voice_42.mp3"


def test_package_gate_rejects_cross_backend_ambiguity(tmp_path: Path):
    _package(tmp_path, "42", "wav")
    (tmp_path / "voice_42.mp3").write_bytes(b"stale")
    with pytest.raises(ProductionMediaError, match="AMBIGUOUS_VOICE_ARTIFACT"):
        verify_production_package(tmp_path, "42")


def test_package_gate_rejects_missing_same_timestamp_artifact(tmp_path: Path):
    _package(tmp_path, "42", "wav")
    (tmp_path / "captions_42.srt").unlink()
    (tmp_path / "captions_41.srt").write_bytes(b"stale")
    with pytest.raises(ProductionMediaError, match="MISSING_PRODUCTION_ARTIFACTS: captions"):
        verify_production_package(tmp_path, "42")
