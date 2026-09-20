from scripts.m6_voice_plan import generate_voice_plan
from scripts.m6_voice_script import normalize


def _assert_exact_spoken_coverage(plan):
    blocks=plan["blocks"]
    assert blocks[0]["spoken_span"]["start"] == 0
    assert blocks[-1]["spoken_span"]["end"] == len(plan["spoken_text"])
    for left,right in zip(blocks, blocks[1:]):
        assert left["spoken_span"]["end"] == right["spoken_span"]["start"]
    rebuilt="".join(plan["spoken_text"][b["spoken_span"]["start"]:b["spoken_span"]["end"]] for b in blocks)
    assert rebuilt == plan["spoken_text"]


def test_deterministic_default_roles_and_exact_coverage():
    n=normalize("AI changed search. Why does it matter? However, latency fell 12%. The result reveals a faster API.")
    a=generate_voice_plan(n); b=generate_voice_plan(n)
    assert a == b
    assert [x["role"] for x in a["blocks"]] == ["HOOK","QUESTION","CONTRAST","REVEAL"]
    _assert_exact_spoken_coverage(a)
    assert a["lexicon_sha256"] == n["lexicon_sha256"]


def test_explicit_semantic_roles_cover_all_supported_roles():
    text="Hook. Question? Contrast. Fact 42. Reveal. Explain. Next step. Finish."
    roles=["HOOK","QUESTION","CONTRAST","IMPORTANT_FACT","REVEAL","EXPLANATION","TRANSITION","CONCLUSION"]
    plan=generate_voice_plan(normalize(text), {"roles": roles})
    assert [b["role"] for b in plan["blocks"]] == roles
    _assert_exact_spoken_coverage(plan)
    assert all(120 <= b["target_wpm"] <= 210 and .8 <= b["rate"] <= 1.2 for b in plan["blocks"])


def test_normalized_number_and_lexicon_keep_display_and_spoken_links():
    n=normalize("AI revenue rose 12.5%. Next, the API explains it.")
    plan=generate_voice_plan(n)
    _assert_exact_spoken_coverage(plan)
    assert plan["display_text"] == "AI revenue rose 12.5%. Next, the API explains it."
    assert plan["spoken_text"].startswith("A I revenue rose twelve point five percent")
    assert "AI" in plan["blocks"][0]["pronunciation_refs"]
    assert "API" in plan["blocks"][1]["pronunciation_refs"]
    assert plan["blocks"][0]["display_span"]["start"] == 0
    assert plan["blocks"][-1]["display_span"]["end"] == len(plan["display_text"])


def test_multi_paragraph_plan_has_no_loss_or_overlap():
    n=normalize("A first explanation.\n\nNow transition.\n\nWhat happens next?")
    plan=generate_voice_plan(n)
    _assert_exact_spoken_coverage(plan)
    assert len(plan["blocks"]) >= 3


def test_unknown_explicit_role_fails_closed():
    try:
        generate_voice_plan(normalize("One sentence."), {"roles":["DRAMATIC"]})
    except ValueError as exc:
        assert "unsupported VoicePlan role" in str(exc)
    else:
        raise AssertionError("unknown role was accepted")
