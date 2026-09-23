import pytest
import scripts.m6_production_alignment as m

def test_normalization_handles_punctuation_and_case():
    assert m._norm("Qwen3-TTS,")=="qwen3tts"
    assert m._norm("Don't")=="don't"

def test_alignment_import_is_lazy():
    assert callable(m.align)

def test_one_observation_can_cover_multiple_canonical_tokens_without_loss():
    canonical=[{"text":"twenty"},{"text":"four"},{"text":"hours"}]
    observed=[{"word":"twentyfour","start":1.0,"end":1.6,"score":.9},{"word":"hours","start":1.7,"end":2.0,"score":.8}]
    out=m._bind_tokens(canonical,observed)
    assert [x["text"] for x in out]==["twenty","four","hours"]
    assert out[0]["start_s"]==1.0 and out[1]["end_s"]==1.6
    assert out[2]["start_s"]==1.7 and out[2]["end_s"]==2.0

def test_multiple_observations_can_cover_one_canonical_token_without_loss():
    canonical=[{"text":"Qwen3-TTS"}]
    observed=[{"word":"Qwen3","start":0.0,"end":.3,"score":.9},{"word":"TTS","start":.31,"end":.5,"score":.9}]
    out=m._bind_tokens(canonical,observed)
    assert len(out)==1 and out[0]["start_s"]==0.0 and out[0]["end_s"]==.5

def test_display_token_observation_can_cover_spoken_expansion():
    canonical=[
        {"text":"twenty","display_text":"2026","display_span_id":"display-token:0:0:4"},
        {"text":"twenty","display_text":"2026","display_span_id":"display-token:0:0:4"},
        {"text":"six","display_text":"2026","display_span_id":"display-token:0:0:4"},
        {"text":"systems","display_text":"systems","display_span_id":"display-token:1:5:12"},
    ]
    observed=[{"word":"2026","start":0.0,"end":.6,"score":.9},{"word":"systems","start":.7,"end":1.1,"score":.9}]
    out=m._bind_tokens(canonical,observed)
    assert [x["text"] for x in out]==["twenty","twenty","six","systems"]
    assert out[0]["start_s"]==0.0 and out[2]["end_s"]==.6

def test_boundary_reconciliation_fails_closed_on_text_change():
    with pytest.raises(m.ProductionAlignmentError,match="WHISPERX_TOKEN_MISMATCH"):
        m._bind_tokens([{"text":"Ryan"}],[{"word":"Brian","start":0,"end":1}])

def test_boundary_reconciliation_fails_closed_on_missing_tail():
    with pytest.raises(m.ProductionAlignmentError,match="WHISPERX_COVERAGE_MISMATCH"):
        m._bind_tokens([{"text":"Ryan"},{"text":"voice"}],[{"word":"Ryan","start":0,"end":1}])
