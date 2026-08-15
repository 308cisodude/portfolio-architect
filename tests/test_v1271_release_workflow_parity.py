"""Regression contract for v1.27.1 immutable-publication workflow parity."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]


def _smoke_step(workflow_name: str) -> str:
    workflow = (ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
    start = workflow.index("      - name: Smoke-test provider shell containers\n")
    end = workflow.index(
        "      - name: Scan source, history, and release artifacts for secrets\n",
        start,
    )
    return workflow[start:end]


def test_validate_and_release_use_identical_supervisor_aware_provider_smoke() -> None:
    validate = _smoke_step("validate.yml")
    release = _smoke_step("release.yml")
    assert validate == release
    assert "--network-alias supervisor" in release
    assert '--env "SUPERVISOR_TOKEN=${supervisor_token}"' in release
    assert 'if self.path != "/addons/self/info"' in release
    assert 'if self.path != "/discovery"' in release
    assert 'ssl.create_default_context(cafile="/data/gateway/tls/ca-cert.pem")' in release


def test_v1271_is_release_engineering_only() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    section = changelog.split("## 1.27.1", 1)[1].split("## 1.27.0", 1)[0]
    assert "without changing production integration or Gateway runtime behavior" in section
    assert "immutable-release" in section
    assert "payload schema 8" in section.lower()
    assert "REST portfolio schema 1" in section
    assert "Gateway health schema 6" in section
