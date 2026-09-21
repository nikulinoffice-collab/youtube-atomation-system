import pytest

from scripts.m6_alignment import AlignmentError, WordTiming, canonicalize_observations, validate_timings


def block(block_id="b1", spoken="two point four billion", display="$2.4B", sid="s1", did="d1"):
    return {"block_id": block_id, "spoken_span": {"id": sid, "text": spoken}, "display_span": {"id": did, "text": display}}


def observations(block_id="b1", sid="s1", count=4):
    return [
        {"block_id": block_id, "spoken_span_id": sid, "token_index": i, "start_s": i * 0.25, "end_s": (i + 1) * 0.25, "confidence": 0.95}
        for i in range(count)
    ]


def test_preserves_display_expansion_while_aligning_spoken_words():
    result = canonicalize_observations([block()], observations(), duration_s=1.0)
    assert result["version"] == "m6.alignment.v1"
    assert result["coverage"] == {"expected_words": 4, "aligned_words": 4}
    assert [w["spoken_text"] for w in result["word_timings"]] == ["two", "point", "four", "billion"]
    assert all(w["display_text"] == "$2.4B" for w in result["word_timings"])
    assert all(w["display_span_id"] == "d1" for w in result["word_timings"])


def test_numbers_dates_acronyms_and_punctuation_are_canonical_not_aligner_text():
    blocks = [
        block("b1", "two point four billion", "$2.4B", "s1", "d1"),
        block("b2", "September twenty first twenty twenty six", "September 21, 2026", "s2", "d2"),
        block("b3", "A I changes quickly", "AI changes quickly.", "s3", "d3"),
    ]
    obs = observations("b1", "s1", 4)
    obs += [{"block_id": "b2", "spoken_span_id": "s2", "token_index": i, "start_s": 1 + i*.2, "end_s": 1.2 + i*.2, "confidence": .9} for i in range(6)]
    obs += [{"block_id": "b3", "spoken_span_id": "s3", "token_index": i, "start_s": 2.2 + i*.2, "end_s": 2.4 + i*.2, "confidence": .9} for i in range(4)]
    result = canonicalize_observations(blocks, obs, duration_s=3.0)
    assert result["coverage"]["expected_words"] == 14
    assert result["word_timings"][4]["display_text"] == "September 21, 2026"
    assert result["word_timings"][10]["display_text"] == "AI changes quickly."


def test_multi_block_order_is_canonical_even_if_observations_arrive_unsorted():
    blocks = [block("b1", "hello world", "Hello world.", "s1", "d1"), block("b2", "next fact", "Next fact.", "s2", "d2")]
    obs = [
        {"block_id":"b2","spoken_span_id":"s2","token_index":1,"start_s":.75,"end_s":1.0,"confidence":1},
        {"block_id":"b1","spoken_span_id":"s1","token_index":0,"start_s":0,"end_s":.25,"confidence":1},
        {"block_id":"b2","spoken_span_id":"s2","token_index":0,"start_s":.5,"end_s":.75,"confidence":1},
        {"block_id":"b1","spoken_span_id":"s1","token_index":1,"start_s":.25,"end_s":.5,"confidence":1},
    ]
    result = canonicalize_observations(blocks, obs, duration_s=1.0)
    assert [(w["block_id"], w["token_index"]) for w in result["word_timings"]] == [("b1",0),("b1",1),("b2",0),("b2",1)]


@pytest.mark.parametrize("mutation,code", [
    ("missing", "MISSING_COVERAGE"),
    ("duplicate", "DUPLICATE_WORD"),
    ("unknown", "UNKNOWN_MAPPING"),
])
def test_fail_closed_coverage_and_mapping(mutation, code):
    obs = observations()
    if mutation == "missing": obs.pop()
    elif mutation == "duplicate": obs.append(dict(obs[0]))
    else: obs[0] = dict(obs[0], spoken_span_id="wrong")
    with pytest.raises(AlignmentError) as exc:
        canonicalize_observations([block()], obs, duration_s=2)
    assert exc.value.code == code


def test_rejects_overlap_bad_confidence_and_past_audio_end():
    base = [
        WordTiming("b","s","d",0,"a","a",0,.5,1),
        WordTiming("b","s","d",1,"b","b",.4,.8,1),
    ]
    with pytest.raises(AlignmentError) as exc: validate_timings(base)
    assert exc.value.code == "NON_MONOTONIC_OR_OVERLAP"
    with pytest.raises(AlignmentError) as exc: validate_timings([WordTiming("b","s","d",0,"a","a",0,.5,1.1)])
    assert exc.value.code == "INVALID_CONFIDENCE"
    with pytest.raises(AlignmentError) as exc: validate_timings([WordTiming("b","s","d",0,"a","a",0,1.01,1)], duration_s=1)
    assert exc.value.code == "PAST_AUDIO_END"
