from pathlib import Path
import pytest

from scripts.m6_qwen3_adapter import Qwen3RyanAdapter
from scripts.m6_tts_adapter import SynthesisRequest, TTSAdapterError
from scripts.m6_voice_plan import generate_voice_plan
from scripts.m6_voice_script import normalize


def plan():
    return generate_voice_plan(normalize("AI changed quickly. Why does it matter?"))


def fake_engine(**kwargs):
    assert kwargs["speaker"] == "Ryan"
    assert kwargs["language"] == "English"
    assert kwargs["output_path"].endswith(".wav")
    assert "Semantic flow:" in kwargs["instruction"]
    return {"sample_rate_hz": 24000, "channels": 1, "device": "cpu", "synthesis_seconds": 2.0, "audio_seconds": 4.0}


def test_pinned_adapter_reports_exact_provenance_and_unsupported_controls():
    adapter = Qwen3RyanAdapter(fake_engine)
    result = adapter.synthesize(SynthesisRequest(plan(), Path("out.wav"), "Ryan"))
    assert result.engine_revision == "022e286b98fbec7e1e916cb940cdf532cd9f488e"
    assert result.model_revision == "85e237c12c027371202489a0ec509ded67b5e4b5"
    assert result.model_id == "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
    assert result.voice_id == "Ryan"
    assert result.real_time_factor == 0.5
    assert set(result.unsupported_controls) == {"exact_wpm", "exact_pitch_semitones", "exact_energy"}


def test_non_ryan_request_fails_closed_before_engine():
    called = False
    def engine(**kwargs):
        nonlocal called; called = True
    with pytest.raises(TTSAdapterError) as exc:
        Qwen3RyanAdapter(engine).synthesize(SynthesisRequest(plan(), Path("out.wav"), "Aiden"))
    assert exc.value.code == "FROZEN_VOICE_MISMATCH"
    assert called is False


def test_incomplete_engine_metrics_fail_closed():
    with pytest.raises(TTSAdapterError) as exc:
        Qwen3RyanAdapter(lambda **kwargs: {"sample_rate_hz": 24000}).synthesize(SynthesisRequest(plan(), Path("out.wav"), "Ryan"))
    assert exc.value.code == "ENGINE_RESULT_INCOMPLETE"


def test_invalid_plan_never_reaches_qwen_boundary():
    called = False
    def engine(**kwargs):
        nonlocal called; called = True
    broken = plan(); broken["blocks"] = []
    with pytest.raises(TTSAdapterError) as exc:
        Qwen3RyanAdapter(engine).synthesize(SynthesisRequest(broken, Path("out.wav"), "Ryan"))
    assert exc.value.code == "INVALID_VOICE_PLAN"
    assert called is False
