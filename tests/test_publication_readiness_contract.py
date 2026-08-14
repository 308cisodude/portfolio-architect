"""v1.17.1 publication-readiness contracts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_publication_metadata_and_docs_are_present() -> None:
    required = [
        "LICENSE",
        "SECURITY.md",
        "SUPPORT.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "publication.json",
        "hacs.json",
        "pyproject.toml",
        "SBOM.spdx.json",
        ".github/workflows/validate.yml",
        ".github/workflows/hacs.yml",
        ".github/workflows/hassfest.yml",
        ".github/workflows/release.yml",
        ".github/dependabot.yml",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/pull_request_template.md",
        "docs/ARCHITECTURE.md",
        "docs/OPERATIONS.md",
        "docs/PUBLISHING.md",
        "docs/PRIVACY.md",
        "docs/QUALITY.md",
        "docs/QUALITY-SCALE-AUDIT.md",
        "docs/SUPPORTED-VERSIONS.md",
        "docs/PUBLICATION-SETUP.md",
        "docs/UPGRADE-1.15.0.md",
        "docs/UPGRADE-1.19.0.md",
        "docs/UPGRADE-1.19.1.md",
        "docs/UPGRADE-1.21.0.md",
        "docs/UPGRADE-1.26.4.md",
        "AI_POLICY.md",
    ]
    for relative in required:
        assert (ROOT / relative).is_file(), relative
    sbom = json.loads((ROOT / "SBOM.spdx.json").read_text())
    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert {package["versionInfo"] for package in sbom["packages"][:2]} == {"1.26.4"}


def test_release_and_operational_tools_have_expected_modes() -> None:
    python_tools = [
        "tools/build_release.py",
        "tools/verify_release.py",
        "tools/configure_publication.py",
        "tools/check_publication.py",
        "tools/check_privacy.py",
    ]
    shell_tools = [
        "tools/release_check.sh",
        "tools/create_backup.sh",
        "tools/rollback_home_assistant.sh",
        "tools/prune_backups.sh",
    ]
    for relative in python_tools:
        path = ROOT / relative
        assert path.is_file()
        assert path.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3")
    for relative in shell_tools:
        path = ROOT / relative
        assert path.is_file()
        assert path.stat().st_mode & 0o100
    prune = (ROOT / "tools/prune_backups.sh").read_text()
    assert "Dry run only" in prune
    assert "find " not in prune
    rollback = (ROOT / "tools/rollback_home_assistant.sh").read_text()
    assert "ha core check" in rollback
    assert "pre-rollback" in rollback


def test_reproducible_release_build(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    for output in (first, second):
        subprocess.run(
            ["python", str(ROOT / "tools/build_release.py"), "--output", str(output)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["python", str(ROOT / "tools/verify_release.py"), "--dist", str(output)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    first_files = sorted(path.name for path in first.iterdir())
    second_files = sorted(path.name for path in second.iterdir())
    assert first_files == second_files
    assert {_sha256(first / name) for name in first_files} == {
        _sha256(second / name) for name in second_files
    }
