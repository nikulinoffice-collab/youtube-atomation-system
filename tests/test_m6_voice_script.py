import json
from pathlib import Path
from scripts.m6_voice_script import normalize, validate

def test_core_normalization_and_mapping():
    r=normalize("AI revenue rose 12.5% to $2.4B in 2026.")
    assert r["spoken_text"] == "A I revenue rose twelve point five percent to two point four billion dollars in twenty twenty six."
    assert r["display_text"] == "AI revenue rose 12.5% to $2.4B in 2026."
    validate(r)
    assert all(r["display_text"][m["display_start"]:m["display_end"]] == m["display"] for m in r["mappings"])

def test_deterministic_and_provenance_stable():
    text="Qwen3-TTS processed 42 items through the API."
    a=normalize(text); b=normalize(text)
    assert a == b
    assert len(a["lexicon_sha256"]) == 64
    validate(a)

def test_no_change_preserves_canonical_text():
    text="Ryan speaks naturally."
    r=normalize(text)
    assert r["display_text"] == text == r["spoken_text"]
    assert r["mappings"] == []

def test_compact_currency_precedes_plain_number_rules():
    r=normalize("The project cost $1.5M.")
    assert r["spoken_text"] == "The project cost one point five million dollars."
    assert len(r["mappings"]) == 1

def test_iso_date_is_single_traceable_edit():
    r=normalize("Launch is 2026-09-20.")
    assert r["spoken_text"] == "Launch is September twentieth twenty twenty six."
    assert len(r["mappings"]) == 1
    assert r["mappings"][0]["rule"] == "iso_date"
    validate(r)

def test_time_normalization_with_and_without_meridiem():
    assert normalize("Meet at 9:05 AM.")["spoken_text"] == "Meet at nine oh five A M."
    assert normalize("Render at 14:30.")["spoken_text"] == "Render at fourteen thirty."

def test_units_precede_plain_number_rules():
    r=normalize("The line is 38.5 km and latency is 12 ms at 24 kHz.")
    assert r["spoken_text"] == "The line is thirty eight point five kilometers and latency is twelve milliseconds at twenty four kilohertz."
    assert [m["rule"] for m in r["mappings"]] == ["unit","unit","unit"]
    validate(r)

def test_invalid_calendar_or_clock_like_values_do_not_claim_date_time_rule():
    r=normalize("Keep 2026-13-40 and 25:99 literal except generic numeric normalization.")
    assert all(m["rule"] not in {"iso_date","time"} for m in r["mappings"])
    validate(r)

def test_frozen_corpus_is_deterministic_and_valid():
    corpus=json.loads((Path(__file__).parents[1]/"docs/m6/benchmark_corpus.json").read_text())
    texts=[]
    def walk(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k in {"text","source_text","display_text"} and isinstance(v,str): texts.append(v)
                else: walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(corpus)
    assert texts
    for text in texts:
        a=normalize(text); b=normalize(text)
        assert a == b
        assert a["display_text"] == text
        validate(a)
