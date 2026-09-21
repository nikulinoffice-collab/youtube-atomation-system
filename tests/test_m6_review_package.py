import hashlib
import json

import pytest

from scripts.m6_review_package import ReviewPackageError, build_review_manifest, write_review_manifest

ROLES = ["HOOK", "QUESTION", "CONTRAST", "IMPORTANT_FACT", "REVEAL", "EXPLANATION", "TRANSITION", "CONCLUSION"]


def fixture(tmp_path):
    audio = tmp_path / "complete-short.wav"
    audio.write_bytes(b"RIFF deterministic review fixture")
    sha = hashlib.sha256(audio.read_bytes()).hexdigest()
    blocks = [{"block_id": f"b{i}", "role": role} for i, role in enumerate(ROLES)]
    plan = {"version": "voiceplan.v1", "blocks": blocks}
    alignment = {"version": "alignment.v1", "word_timings": [{"block_id": b["block_id"], "start_s": i, "end_s": i + .5} for i, b in enumerate(blocks)]}
    qc = {"version": "m6.qc.v1", "status": "HUMAN_REVIEW_REQUIRED_M6_8", "naturalness_claimed": False, "production_migration_permitted": False, "audit": {"audio_sha256": sha, "block_ids": [b["block_id"] for b in blocks]}}
    cases = [{"case_id": "complete-short", "purpose": "all directed roles"}, {"case_id": "numbers", "purpose": "display/spoken expansion"}]
    return audio, plan, alignment, qc, cases


def test_manifest_is_reproducible_and_human_gated(tmp_path):
    args = fixture(tmp_path)
    a = build_review_manifest(audio_path=args[0], plan=args[1], alignment=args[2], qc=args[3], representative_cases=args[4])
    b = build_review_manifest(audio_path=args[0], plan=args[1], alignment=args[2], qc=args[3], representative_cases=args[4])
    assert a == b
    assert a["status"] == "HUMAN_REVIEW_REQUIRED_M6_8"
    assert a["m6_9_autostart_permitted"] is False
    assert a["human_review"]["required"] is True
    out = tmp_path / "manifest.json"
    write_review_manifest(out, a)
    assert json.loads(out.read_text()) == a


@pytest.mark.parametrize("mutation", ["sha", "status", "production", "role", "alignment", "duplicate_case"])
def test_review_package_fails_closed(tmp_path, mutation):
    audio, plan, alignment, qc, cases = fixture(tmp_path)
    if mutation == "sha": qc["audit"]["audio_sha256"] = "0" * 64
    elif mutation == "status": qc["status"] = "PASS"
    elif mutation == "production": qc["production_migration_permitted"] = True
    elif mutation == "role": plan["blocks"][-1]["role"] = "EXPLANATION"
    elif mutation == "alignment": alignment["word_timings"] = []
    elif mutation == "duplicate_case": cases[1]["case_id"] = cases[0]["case_id"]
    with pytest.raises(ReviewPackageError):
        build_review_manifest(audio_path=audio, plan=plan, alignment=alignment, qc=qc, representative_cases=cases)
