import pytest

from scripts.m6_qc import QCError, screen_qc


def fixture():
    audio = {"duration_s": 2.0, "sha256": "a" * 64}
    plan = {"version": "voiceplan.v1", "blocks": [{"block_id": "b1"}, {"block_id": "b2"}]}
    alignment = {
        "version": "alignment.v1",
        "coverage": {"expected_words": 4, "aligned_words": 4},
        "word_timings": [
            {"block_id": "b1", "start_s": 0.10, "end_s": 0.35, "confidence": 0.98},
            {"block_id": "b1", "start_s": 0.40, "end_s": 0.70, "confidence": 0.97},
            {"block_id": "b2", "start_s": 1.00, "end_s": 1.25, "confidence": 0.96},
            {"block_id": "b2", "start_s": 1.30, "end_s": 1.65, "confidence": 0.95},
        ],
    }
    analysis = {"silence_ratio": 0.18, "clipping_ratio": 0.0, "pitch_range_semitones": 5.2, "energy_dynamic_range_db": 8.0}
    return audio, plan, alignment, analysis


def test_pass_is_screening_only_and_human_gated():
    result = screen_qc(audio=fixture()[0], plan=fixture()[1], alignment=fixture()[2], analysis=fixture()[3])
    assert result["status"] == "HUMAN_REVIEW_REQUIRED_M6_8"
    assert result["screening_only"] is True
    assert result["naturalness_claimed"] is False
    assert result["production_migration_permitted"] is False
    assert result["audit"]["block_ids"] == ["b1", "b2"]
    assert result["metrics"]["wpm"] == 120.0


@pytest.mark.parametrize("mutation,code", [
    ("missing", "ALIGNMENT_COVERAGE"),
    ("reorder", "BLOCK_CONTINUITY"),
    ("overlap", "TIMING_ANOMALY"),
    ("confidence", "INVALID_ALIGNMENT_CONFIDENCE"),
    ("silence", "PATHOLOGICAL_SILENCE"),
    ("clipping", "CLIPPING"),
])
def test_fail_closed_adversarial(mutation, code):
    audio, plan, alignment, analysis = fixture()
    if mutation == "missing": alignment["coverage"]["aligned_words"] = 3
    elif mutation == "reorder": alignment["word_timings"] = alignment["word_timings"][2:] + alignment["word_timings"][:2]
    elif mutation == "overlap": alignment["word_timings"][1]["start_s"] = 0.2
    elif mutation == "confidence": alignment["word_timings"][0]["confidence"] = 1.01
    elif mutation == "silence": analysis["silence_ratio"] = 0.451
    elif mutation == "clipping": analysis["clipping_ratio"] = 0.0011
    with pytest.raises(QCError) as exc: screen_qc(audio=audio, plan=plan, alignment=alignment, analysis=analysis)
    assert exc.value.code == code


def test_boundary_thresholds_are_accepted():
    audio, plan, alignment, analysis = fixture()
    analysis["silence_ratio"] = 0.45
    analysis["clipping_ratio"] = 0.001
    result = screen_qc(audio=audio, plan=plan, alignment=alignment, analysis=analysis)
    assert result["status"] == "HUMAN_REVIEW_REQUIRED_M6_8"


def test_empty_speech_and_empty_plan_fail_closed():
    audio, plan, alignment, analysis = fixture()
    alignment["word_timings"] = []
    with pytest.raises(QCError) as exc: screen_qc(audio=audio, plan=plan, alignment=alignment, analysis=analysis)
    assert exc.value.code == "MISSING_SPEECH"
    audio, plan, alignment, analysis = fixture()
    plan["blocks"] = []
    with pytest.raises(QCError) as exc: screen_qc(audio=audio, plan=plan, alignment=alignment, analysis=analysis)
    assert exc.value.code == "EMPTY_PLAN"
