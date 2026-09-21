from scripts.m6_production_ryan import ProductionRyanError
from pathlib import Path
import json
import pytest
import scripts.m6_production_ryan as mod

def test_import_is_lazy():
    assert callable(mod.synthesize)

def test_frozen_config_is_ryan_and_zero_cost():
    cfg=json.loads(mod.CONFIG.read_text())
    assert cfg["speaker"]=="Ryan"
    assert cfg["paid_services"] is False
    assert cfg["model_revision"]=="85e237c12c027371202489a0ec509ded67b5e4b5"
