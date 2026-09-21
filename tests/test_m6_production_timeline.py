import pytest
from scripts.m6_production_timeline import build_production_timeline, TimelineBridgeError

def test_bridge_preserves_display_text_and_collapses_expansion():
    text="It cost $2.4B."
    aligned=[
      {"display_span_id":"d1","start_s":0.0,"end_s":0.2},
      {"display_span_id":"d2","start_s":0.3,"end_s":0.5},
      {"display_span_id":"d3","start_s":0.6,"end_s":0.7},
      {"display_span_id":"d3","start_s":0.7,"end_s":0.8},
      {"display_span_id":"d3","start_s":0.8,"end_s":1.0},
    ]
    result=build_production_timeline(text,aligned,1.1)
    assert result["text"]==text
    assert "".join(w["separator_before"]+w["word"] for w in result["words"])==text
    assert result["words"][-1]["word"]=="$2.4B."
    assert result["words"][-1]["start"]==0.6 and result["words"][-1]["end"]==1.0

def test_bridge_fails_closed_on_coverage_mismatch():
    with pytest.raises(TimelineBridgeError):
      build_production_timeline("two words", [{"display_span_id":"d1","start_s":0,"end_s":.2}], .3)
