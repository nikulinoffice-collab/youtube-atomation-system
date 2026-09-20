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

def test_frozen_corpus_is_deterministic_and_valid():
    corpus=json.loads((Path(__file__).parents[1]/"docs/m6/benchmark_corpus.json").read_text())
    # Accept either a list or a dict containing case lists; recursively collect text fields.
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
