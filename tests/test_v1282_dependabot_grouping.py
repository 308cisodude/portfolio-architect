"""Regression coverage for v1.32.0 Dependabot GitHub Actions grouping."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPENDABOT = ROOT / ".github" / "dependabot.yml"
WORKFLOWS = ROOT / ".github" / "workflows"
EXPECTED_GROUP = "github-actions-version-updates"
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_PYTHON_SHA = "5fda3b95a4ea91299a34e894583c3862153e4b97"


def _dependabot() -> dict[str, object]:
    document = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_github_actions_version_updates_are_one_explicit_group() -> None:
    config = _dependabot()
    assert config["version"] == 2
    updates = config["updates"]
    assert isinstance(updates, list)
    assert len(updates) == 1
    entry = updates[0]
    assert entry["package-ecosystem"] == "github-actions"
    assert entry["directory"] == "/"
    assert entry["schedule"] == {"interval": "weekly"}
    assert entry["open-pull-requests-limit"] == 5
    assert entry["groups"] == {
        EXPECTED_GROUP: {
            "applies-to": "version-updates",
            "patterns": ["*"],
        }
    }


def test_group_covers_major_minor_and_patch_without_batching_security_updates() -> None:
    entry = _dependabot()["updates"][0]
    group = entry["groups"][EXPECTED_GROUP]
    assert group["applies-to"] == "version-updates"
    assert group["patterns"] == ["*"]
    assert "update-types" not in group
    assert all(
        value.get("applies-to", "version-updates") != "security-updates"
        for value in entry["groups"].values()
    )


def test_grouping_does_not_weaken_immutable_action_pins() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))
    )
    refs = re.findall(r"uses:\s*[^@\s]+@([^\s#]+)", combined)
    assert refs
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in refs)
    assert combined.count(f"actions/checkout@{CHECKOUT_SHA}") == 4
    assert combined.count(f"actions/setup-python@{SETUP_PYTHON_SHA}") == 2
    assert "ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION" not in combined


def test_dependabot_configuration_remains_codeowner_protected() -> None:
    codeowners = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert any(
        line.startswith("/.github/dependabot.yml ")
        for line in codeowners.splitlines()
    )
