from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"
CONSTRAINTS = ROOT / "constraints" / "m6-qualification.txt"
QUALIFICATION = ROOT / ".github" / "workflows" / "m6-qualification.yml"
PUBLISH = ROOT / ".github" / "workflows" / "publish.yml"

_NAME = re.compile(r"^\\s*([A-Za-z0-9_.-]+)")


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _entries(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _NAME.match(line)
        assert match, f"unparseable dependency line in {path}: {line!r}"
        result[_normalize(match.group(1))] = line
    return result


def test_every_direct_production_requirement_is_exactly_constrained() -> None:
    requirements = _entries(REQUIREMENTS)
    constraints = _entries(CONSTRAINTS)
    missing = sorted(set(requirements) - set(constraints))
    assert not missing, f"direct production requirements missing from constraints: {missing}"
    for name in requirements:
        line = constraints[name]
        assert "==" in line, f"{name} is not exact-pinned in constraints: {line}"


def test_frozen_voice_runtime_versions_are_preserved() -> None:
    constraints = _entries(CONSTRAINTS)
    assert constraints["qwen-tts"] == "qwen-tts==0.1.1"
    assert constraints["whisperx"] == "whisperx==3.8.6"


def test_qualification_and_draft_use_same_production_constraints() -> None:
    qualification = QUALIFICATION.read_text(encoding="utf-8")
    publish = PUBLISH.read_text(encoding="utf-8")
    install = "python -m pip install -r requirements.txt -c constraints/m6-qualification.txt"
    assert install in qualification
    assert install in publish
    assert "constraints/**" in qualification
    assert "python -m pip check" in qualification
    assert "python -m pip check" in publish


def test_python_and_runner_identity_are_explicit() -> None:
    qualification = QUALIFICATION.read_text(encoding="utf-8")
    publish = PUBLISH.read_text(encoding="utf-8")
    assert "runs-on: ubuntu-24.04" in qualification
    assert "runs-on: ubuntu-24.04" in publish
    assert "python-version: '3.11'" in qualification
    assert 'python-version: "3.11"' in publish
