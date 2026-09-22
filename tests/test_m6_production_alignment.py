import pytest
import scripts.m6_production_alignment as m

def test_normalization_handles_punctuation_and_case():
    assert m._norm("Qwen3-TTS,")=="qwen3tts"
    assert m._norm("Don't")=="don't"

def test_alignment_import_is_lazy():
    assert callable(m.align)
