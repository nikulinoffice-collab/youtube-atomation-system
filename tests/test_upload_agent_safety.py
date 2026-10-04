import ast
import os
from pathlib import Path

import pytest


SOURCE_PATH = Path(__file__).parents[1] / "agents" / "upload_agent.py"


def _tree():
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))


def _assignment(name):
    for node in _tree().body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} assignment not found")


def _function(name):
    for node in _tree().body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found")


def test_upload_defaults_to_private():
    assert _assignment("PRIVACY_STATUS") == "private"


def test_authorization_is_first_main_operation():
    main = _function("main")
    first = main.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Call)
    assert isinstance(first.value.func, ast.Name)
    assert first.value.func.id == "require_publish_authorization"


def test_unauthorized_gate_fails_closed_before_main_can_continue(monkeypatch):
    gate = _function("require_publish_authorization")
    module = ast.Module(body=[gate], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"os": os, "SystemExit": SystemExit}
    exec(compile(module, str(SOURCE_PATH), "exec"), namespace)

    monkeypatch.delenv("YOUTUBE_PUBLISH_AUTHORIZED", raising=False)
    with pytest.raises(SystemExit, match="publishing is disabled by default"):
        namespace["require_publish_authorization"]()


def test_authorized_gate_accepts_only_explicit_true(monkeypatch):
    gate = _function("require_publish_authorization")
    module = ast.Module(body=[gate], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"os": os, "SystemExit": SystemExit}
    exec(compile(module, str(SOURCE_PATH), "exec"), namespace)

    for value in ("1", "yes", "enabled", "false", ""):
        monkeypatch.setenv("YOUTUBE_PUBLISH_AUTHORIZED", value)
        with pytest.raises(SystemExit):
            namespace["require_publish_authorization"]()

    monkeypatch.setenv("YOUTUBE_PUBLISH_AUTHORIZED", "true")
    namespace["require_publish_authorization"]()
