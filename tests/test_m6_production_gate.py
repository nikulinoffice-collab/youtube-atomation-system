import json
from pathlib import Path
import pytest
from scripts.m6_production_gate import qualify, ProductionGateError, EVIDENCE

def approval(**extra):
    value = dict(EVIDENCE)
    value.update({"human_review_approved": True, "publishing_rights_blocker": False})
    value.update(extra)
    return value

def rollback(**extra):
    value = {"enabled": True, "target": "edge-production", "automatic_on_failure": True}
    value.update(extra)
    return value

def test_approved_configuration_qualifies_without_quality_change():
    result = qualify(approval(), rollback())
    assert result["qualified"] is True
    assert result["voice"] == "Ryan"
    assert result["quality_configuration_changed"] is False

def test_human_review_is_required():
    with pytest.raises(ProductionGateError) as exc:
        qualify(approval(human_review_approved=False), rollback())
    assert exc.value.code == "HUMAN_REVIEW_REQUIRED"

def test_rights_blocker_fails_closed():
    with pytest.raises(ProductionGateError) as exc:
        qualify(approval(publishing_rights_blocker=True), rollback())
    assert exc.value.code == "RIGHTS_BLOCKED"

@pytest.mark.parametrize("field", list(EVIDENCE))
def test_evidence_drift_fails_closed(field):
    value = approval()
    value[field] = "wrong"
    with pytest.raises(ProductionGateError) as exc:
        qualify(value, rollback())
    assert exc.value.code == "EVIDENCE_MISMATCH"

def test_rollback_is_required():
    with pytest.raises(ProductionGateError) as exc:
        qualify(approval(), rollback(enabled=False))
    assert exc.value.code == "ROLLBACK_REQUIRED"

def test_config_drift_fails_closed(tmp_path):
    cfg = json.loads(Path("config/m6/qwen3_ryan_frozen.json").read_text())
    cfg["speaker"] = "Aiden"
    path = tmp_path / "config.json"
    path.write_text(json.dumps(cfg))
    with pytest.raises(ProductionGateError) as exc:
        qualify(approval(), rollback(), path)
    assert exc.value.code == "CONFIG_DRIFT"
