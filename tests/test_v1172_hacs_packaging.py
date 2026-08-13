"""v1.18.1 HACS packaging regression contracts."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _build(output: Path) -> None:
    subprocess.run(
        ["python", str(ROOT / "tools/build_release.py"), "--output", str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_release_verifier_accepts_channel_specific_layouts(tmp_path: Path) -> None:
    _build(tmp_path)
    subprocess.run(
        ["python", str(ROOT / "tools/verify_release.py"), "--dist", str(tmp_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_release_verifier_rejects_dropin_used_as_hacs_asset(tmp_path: Path) -> None:
    _build(tmp_path)
    broken_hacs = tmp_path / "portfolio_architect.zip"
    shutil.copy2(
        tmp_path / "portfolio-architect-v1.24.0-ha-dropin.zip",
        broken_hacs,
    )
    digest = hashlib.sha256(broken_hacs.read_bytes()).hexdigest()
    checksums = tmp_path / "SHA256SUMS"
    lines = [
        f"{digest}  portfolio_architect.zip"
        if line.endswith("  portfolio_architect.zip")
        else line
        for line in checksums.read_text(encoding="utf-8").splitlines()
    ]
    checksums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = subprocess.run(
        ["python", str(ROOT / "tools/verify_release.py"), "--dist", str(tmp_path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "custom_components/ prefix" in (result.stdout + result.stderr)
