"""Regression coverage for v1.34.0 GitHub Actions runtime maintenance."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_PYTHON_SHA = "5fda3b95a4ea91299a34e894583c3862153e4b97"
OLD_CHECKOUT_SHA = "11d5960a326750d5838078e36cf38b85af677262"
OLD_SETUP_PYTHON_SHA = "a26af69be951a213d495a4c3e4e4022e16d87065"


def _workflow_texts() -> dict[str, str]:
    paths = sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))
    return {path.name: path.read_text(encoding="utf-8") for path in paths}


def test_checkout_v7_is_pinned_everywhere_and_node20_pin_is_gone() -> None:
    workflows = _workflow_texts()
    refs = []
    for name, text in workflows.items():
        refs.extend((name, match.group(1)) for match in re.finditer(r"actions/checkout@([^\s]+)", text))
    assert {name for name, _ in refs} == {"hacs.yml", "hassfest.yml", "validate.yml", "release.yml"}
    assert len(refs) == 4
    assert all(ref == CHECKOUT_SHA for _, ref in refs)
    assert all(f"actions/checkout@{CHECKOUT_SHA} # v7.0.1" in workflows[name] for name, _ in refs)
    assert all(OLD_CHECKOUT_SHA not in text for text in workflows.values())


def test_setup_python_v7_is_pinned_in_validate_and_release_only() -> None:
    workflows = _workflow_texts()
    refs = []
    for name, text in workflows.items():
        refs.extend((name, match.group(1)) for match in re.finditer(r"actions/setup-python@([^\s]+)", text))
    assert set(refs) == {("release.yml", SETUP_PYTHON_SHA), ("validate.yml", SETUP_PYTHON_SHA)}
    assert len(refs) == 2
    assert f"actions/setup-python@{SETUP_PYTHON_SHA} # v7.0.0" in workflows["validate.yml"]
    assert f"actions/setup-python@{SETUP_PYTHON_SHA} # v7.0.0" in workflows["release.yml"]
    assert all(OLD_SETUP_PYTHON_SHA not in text for text in workflows.values())


def test_action_runtime_refresh_keeps_immutable_refs_and_rejects_node20_escape_hatch() -> None:
    workflows = _workflow_texts()
    combined = "\n".join(workflows.values())
    assert "ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION" not in combined
    assert "actions/checkout@v7" not in combined
    assert "actions/setup-python@v7" not in combined
    for action in ("actions/checkout", "actions/setup-python"):
        refs = re.findall(rf"{re.escape(action)}@([^\s]+)", combined)
        assert refs
        assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in refs)


def test_validate_and_release_keep_python_and_runner_contracts() -> None:
    for name in ("validate.yml", "release.yml"):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "runs-on: ubuntu-24.04" in text
        assert 'python-version: "3.14.6"' in text
        assert "cache: pip" in text
        assert "cache-dependency-path: requirements/ci-python-3.14-linux-x86_64.txt" in text
