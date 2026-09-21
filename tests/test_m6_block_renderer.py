import hashlib
import wave

import pytest

from scripts.m6_block_renderer import BlockRenderError, assemble_lossless_wav, render_voice_plan_blocks, stable_block_id
from scripts.m6_voice_plan import generate_voice_plan
from scripts.m6_voice_script import normalize

VOICE = "Ryan"
MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
REV = "85e237c"


def _plan(text="Hook this. Why now? However, latency fell 12%. The result reveals the answer."):
    return generate_voice_plan(normalize(text))


def _write_wav(path, frames, rate=24000, channels=1, width=2):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        wav.writeframes(frames)


def _renderer(frames=b"\x01\x00" * 240):
    def render(block, out):
        _write_wav(out, frames)
        return {"voice_id": VOICE, "model_id": MODEL, "model_revision": REV}
    return render


def _render(tmp_path, plan=None, renderer=None):
    plan = plan or _plan()
    manifest = render_voice_plan_blocks(plan, tmp_path, renderer or _renderer(), voice_id=VOICE, model_id=MODEL, model_revision=REV)
    return plan, manifest


def test_stable_ids_and_exact_multi_block_order(tmp_path):
    plan = _plan()
    _, a = _render(tmp_path / "a", plan)
    _, b = _render(tmp_path / "b", plan)
    expected = [stable_block_id(plan, block) for block in plan["blocks"]]
    assert [r["block_id"] for r in a["blocks"]] == expected
    assert [r["block_id"] for r in b["blocks"]] == expected
    assert [r["index"] for r in a["blocks"]] == list(range(len(plan["blocks"])))


def test_lossless_assembly_is_exact_pcm_concatenation(tmp_path):
    plan, manifest = _render(tmp_path / "blocks")
    result = assemble_lossless_wav(manifest, tmp_path / "blocks", tmp_path / "full.wav")
    with wave.open(str(tmp_path / "full.wav"), "rb") as wav:
        pcm = wav.readframes(wav.getnframes())
        assert wav.getframerate() == 24000
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
    expected = b"".join(b"\x01\x00" * 240 for _ in plan["blocks"])
    assert pcm == expected
    assert result["pcm_bytes"] == len(expected)
    assert result["assembly"] == "lossless_pcm_concatenation"


def test_full_short_scale_plan_preserves_semantic_flow(tmp_path):
    text = ("AI changed search overnight. Why does that matter for creators? However, latency fell twelve percent. "
            "The important fact is that responses arrive faster. The result reveals a simpler workflow. "
            "This explains why teams can iterate more quickly. Next, measure the real audience response. "
            "That is the practical conclusion.")
    roles = ["HOOK", "QUESTION", "CONTRAST", "IMPORTANT_FACT", "REVEAL", "EXPLANATION", "TRANSITION", "CONCLUSION"]
    plan = generate_voice_plan(normalize(text), {"roles": roles})
    _, manifest = _render(tmp_path / "blocks", plan)
    assert [r["role"] for r in manifest["blocks"]] == roles
    assert manifest["blocks"][-1]["spoken_span"]["end"] == len(plan["spoken_text"])
    assembled = assemble_lossless_wav(manifest, tmp_path / "blocks", tmp_path / "short.wav")
    assert assembled["block_count"] == 8


def test_reordered_or_gapped_plan_fails_before_render(tmp_path):
    plan = _plan()
    plan["blocks"][1]["spoken_span"]["start"] += 1
    with pytest.raises(BlockRenderError) as exc:
        _render(tmp_path, plan)
    assert exc.value.code == "BLOCK_ORDER_OR_COVERAGE"


def test_identity_drift_fails_closed(tmp_path):
    def drift(block, out):
        _write_wav(out, b"\0\0" * 20)
        return {"voice_id": "Other", "model_id": MODEL, "model_revision": REV}
    with pytest.raises(BlockRenderError) as exc:
        _render(tmp_path, renderer=drift)
    assert exc.value.code == "RENDER_IDENTITY_DRIFT"


def test_format_drift_fails_closed(tmp_path):
    calls = 0
    def drift(block, out):
        nonlocal calls
        calls += 1
        _write_wav(out, b"\0\0" * 20, rate=24000 if calls == 1 else 22050)
        return {"voice_id": VOICE, "model_id": MODEL, "model_revision": REV}
    with pytest.raises(BlockRenderError) as exc:
        _render(tmp_path, renderer=drift)
    assert exc.value.code == "WAV_FORMAT_DRIFT"


def test_missing_audio_fails_closed(tmp_path):
    def missing(block, out):
        return {"voice_id": VOICE, "model_id": MODEL, "model_revision": REV}
    with pytest.raises(BlockRenderError) as exc:
        _render(tmp_path, renderer=missing)
    assert exc.value.code == "MISSING_BLOCK_AUDIO"


def test_tampered_block_is_rejected_at_assembly(tmp_path):
    _, manifest = _render(tmp_path / "blocks")
    first = tmp_path / "blocks" / manifest["blocks"][0]["wav"]
    with first.open("ab") as fh:
        fh.write(b"tamper")
    with pytest.raises(BlockRenderError) as exc:
        assemble_lossless_wav(manifest, tmp_path / "blocks", tmp_path / "full.wav")
    assert exc.value.code == "BLOCK_HASH_MISMATCH"


def test_manifest_duplicate_and_order_detection(tmp_path):
    _, manifest = _render(tmp_path / "blocks")
    manifest["blocks"][1]["index"] = 0
    with pytest.raises(BlockRenderError) as exc:
        assemble_lossless_wav(manifest, tmp_path / "blocks", tmp_path / "full.wav")
    assert exc.value.code == "MANIFEST_ORDER_INVALID"
