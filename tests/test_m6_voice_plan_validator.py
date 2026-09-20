from copy import deepcopy
import pytest
from scripts.m6_voice_script import normalize
from scripts.m6_voice_plan import generate_voice_plan
from scripts.m6_voice_plan_validator import validate_voice_plan, VoicePlanValidationError

def fixture():
    n=normalize("AI revenue rose 12.5%. Why does it matter? The result reveals the answer.")
    return n,generate_voice_plan(n),{"AI","API","TTS","Qwen3-TTS","GitHub"}

def reject(mutator,code):
    n,p,known=fixture(); bad=deepcopy(p); mutator(bad)
    with pytest.raises(VoicePlanValidationError) as exc: validate_voice_plan(bad,n,known)
    assert code in {e.code for e in exc.value.errors}
    assert exc.value.as_dict()["valid"] is False

def test_valid_plan_passes():
    n,p,k=fixture(); assert validate_voice_plan(p,n,k)=={"valid":True,"errors":[]}

def test_rejects_source_provenance_mismatch(): reject(lambda p:p.__setitem__("lexicon_sha256","0"*64),"PROVENANCE")
def test_rejects_missing_spoken_coverage(): reject(lambda p:p["blocks"].pop(1),"COVERAGE")
def test_rejects_duplicated_block(): reject(lambda p:p["blocks"].insert(1,deepcopy(p["blocks"][0])),"BLOCK_ID")
def test_rejects_reordered_blocks(): reject(lambda p:p["blocks"].reverse(),"COVERAGE")
def test_rejects_unknown_role(): reject(lambda p:p["blocks"][0].__setitem__("role","DRAMA"),"ROLE")
def test_rejects_excessive_wpm(): reject(lambda p:p["blocks"][0].__setitem__("target_wpm",300),"BOUNDS")
def test_rejects_invalid_pause(): reject(lambda p:p["blocks"][0].__setitem__("post_pause_ms",5000),"BOUNDS")
def test_rejects_unknown_pronunciation_reference(): reject(lambda p:p["blocks"][0].__setitem__("pronunciation_refs",["UNKNOWN"]),"PRONUNCIATION")
def test_rejects_emphasis_outside_block():
    def mutate(p): p["blocks"][0]["emphasis"]=[{"spoken_span":{"start":999,"end":1000},"strength":"moderate"}]
    reject(mutate,"EMPHASIS")
