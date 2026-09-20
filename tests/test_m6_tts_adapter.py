from dataclasses import replace
from pathlib import Path

import pytest

from scripts.m6_voice_plan import build_voice_plan
from scripts.m6_tts_adapter import SynthesisRequest, SynthesisResult, TTSAdapter, TTSAdapterError
from scripts.m6_voice_script import normalize


class FakeAdapter(TTSAdapter):
    adapter_id = "fake"

    def __init__(self):
        self.engine_called = False
        self.override = None

    def _synthesize_validated(self, request):
        self.engine_called = True
        result = SynthesisResult(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            engine_id="fake-engine",
            engine_revision="engine-sha",
            model_id="fake-model",
            model_revision="model-sha",
            voice_id=request.voice_id,
            output_path=request.output_path,
            audio_format="wav",
            sample_rate_hz=24000,
            channels=1,
            device="cpu-test-double",
            synthesis_seconds=0.5,
            audio_seconds=1.0,
            real_time_factor=0.5,
            unsupported_controls=("pitch_range_semitones",),
        )
        return self.override(result) if self.override else result


def plan(text="AI changed the result."):
    return build_voice_plan(normalize(text))


def request(p=None, path=Path("voice.wav"), voice="test-voice"):
    return SynthesisRequest(p or plan(), path, voice)


def test_valid_plan_crosses_vendor_neutral_boundary_with_provenance():
    adapter = FakeAdapter()
    result = adapter.synthesize(request())
    assert adapter.engine_called
    assert result.provenance()["model_revision"] == "model-sha"
    assert result.unsupported_controls == ("pitch_range_semitones",)


def test_invalid_plan_is_fail_closed_before_engine_call():
    adapter = FakeAdapter()
    bad = plan()
    bad["blocks"][0]["target_wpm"] = 999
    with pytest.raises(TTSAdapterError) as exc:
        adapter.synthesize(request(bad))
    assert exc.value.code == "INVALID_VOICE_PLAN"
    assert not adapter.engine_called


def test_requires_lossless_wav_before_engine_call():
    adapter = FakeAdapter()
    with pytest.raises(TTSAdapterError) as exc:
        adapter.synthesize(request(path=Path("voice.mp3")))
    assert exc.value.code == "LOSSLESS_WAV_REQUIRED"
    assert not adapter.engine_called


def test_rejects_voice_provenance_drift():
    adapter = FakeAdapter()
    adapter.override = lambda r: replace(r, voice_id="different-voice")
    with pytest.raises(TTSAdapterError) as exc:
        adapter.synthesize(request())
    assert exc.value.code == "VOICE_PROVENANCE_MISMATCH"


def test_rejects_incomplete_engine_model_provenance():
    adapter = FakeAdapter()
    adapter.override = lambda r: replace(r, model_revision="")
    with pytest.raises(TTSAdapterError) as exc:
        adapter.synthesize(request())
    assert exc.value.code == "INCOMPLETE_PROVENANCE"


def test_rejects_invalid_runtime_metrics():
    adapter = FakeAdapter()
    adapter.override = lambda r: replace(r, audio_seconds=0.0)
    with pytest.raises(TTSAdapterError) as exc:
        adapter.synthesize(request())
    assert exc.value.code == "INVALID_RUNTIME_METRICS"
