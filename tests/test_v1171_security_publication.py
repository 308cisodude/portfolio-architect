"""v1.17.x security-hardened publication contracts."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_unconfigured_source_is_fail_closed_without_invented_urls(
    tmp_path: Path,
) -> None:
    target = tmp_path / "unconfigured-repository"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns("dist", ".pytest_cache", "__pycache__", "*.pyc"),
    )

    manifest_path = target / "custom_components/portfolio_architect/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["codeowners"] = []
    manifest.pop("documentation", None)
    manifest.pop("issue_tracker", None)
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    publication = {
        "schema": 1,
        "configured": False,
        "github_repository": "",
        "codeowners": [],
    }
    (target / "publication.json").write_text(
        json.dumps(publication, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target / ".github/CODEOWNERS").unlink(missing_ok=True)

    subprocess.run(
        ["python", str(target / "tools/check_publication.py"), "--root", str(target)],
        cwd=target,
        check=True,
        capture_output=True,
        text=True,
    )
    strict = subprocess.run(
        [
            "python",
            str(target / "tools/check_publication.py"),
            "--root",
            str(target),
            "--strict",
        ],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    assert strict.returncode != 0
    assert "not configured" in (strict.stdout + strict.stderr)


def test_publication_configurator_writes_real_repository_contract(tmp_path: Path) -> None:
    target = tmp_path / "repository"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns("dist", ".pytest_cache", "__pycache__", "*.pyc"),
    )
    subprocess.run(
        [
            "python",
            str(target / "tools/configure_publication.py"),
            "--root",
            str(target),
            "--repository",
            "octocat/portfolio-architect",
            "--codeowner",
            "@octocat",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "python",
            str(target / "tools/check_publication.py"),
            "--root",
            str(target),
            "--strict",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(
        (target / "custom_components/portfolio_architect/manifest.json").read_text()
    )
    assert manifest["documentation"] == (
        "https://github.com/octocat/portfolio-architect#readme"
    )
    assert manifest["issue_tracker"] == (
        "https://github.com/octocat/portfolio-architect/issues"
    )
    assert manifest["codeowners"] == ["@octocat"]
    keys = list(manifest)
    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])
    codeowners = (target / ".github/CODEOWNERS").read_text()
    assert "@octocat" in codeowners
    assert "/.github/workflows/ @octocat" in codeowners
    assert "/tools/check_publication.py @octocat" in codeowners
    assert not (target / ".github/CODEOWNERS.example").exists()
    assert not (target / "PACKAGE-MANIFEST.json").exists()
    assert not (target / "SHA256SUMS").exists()


def test_hacs_metadata_and_stable_release_archive(tmp_path: Path) -> None:
    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert hacs == {
        "name": "Portfolio Architect",
        "render_readme": True,
        "zip_release": True,
        "filename": "portfolio_architect.zip",
        "homeassistant": "2026.7.0",
    }
    subprocess.run(
        ["python", str(ROOT / "tools/build_release.py"), "--output", str(tmp_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    stable = tmp_path / "portfolio_architect.zip"
    versioned = tmp_path / "portfolio-architect-v1.21.0-ha-dropin.zip"
    assert stable.is_file()
    assert versioned.is_file()
    assert _sha256(stable) != _sha256(versioned)

    with zipfile.ZipFile(stable) as archive:
        hacs_payload = {
            info.filename: hashlib.sha256(archive.read(info)).hexdigest()
            for info in archive.infolist()
            if not info.is_dir()
        }
    assert "manifest.json" in hacs_payload
    assert "brand/icon.png" in hacs_payload
    assert not any(name.startswith("custom_components/") for name in hacs_payload)

    prefix = "custom_components/portfolio_architect/"
    with zipfile.ZipFile(versioned) as archive:
        dropin_payload = {
            info.filename.removeprefix(prefix): hashlib.sha256(archive.read(info)).hexdigest()
            for info in archive.infolist()
            if not info.is_dir()
        }
        assert all(
            info.filename.startswith(prefix)
            for info in archive.infolist()
            if not info.is_dir()
        )
    assert dropin_payload == hacs_payload


def test_publication_workflows_use_immutable_dependencies() -> None:
    hacs = (ROOT / ".github/workflows/hacs.yml").read_text()
    hassfest = (ROOT / ".github/workflows/hassfest.yml").read_text()
    validate = (ROOT / ".github/workflows/validate.yml").read_text()
    release = (ROOT / ".github/workflows/release.yml").read_text()
    workflows = "\n".join((hacs, hassfest, validate, release))

    assert "@main" not in workflows
    assert "@master" not in workflows
    assert "@v4" not in workflows
    assert "@v5" not in workflows
    assert ":latest" not in workflows
    assert "ubuntu-latest" not in workflows
    assert workflows.count("runs-on: ubuntu-24.04") == 4
    assert "ghcr.io/hacs/action@sha256:a713e16" in hacs
    assert "ghcr.io/home-assistant/hassfest@sha256:5bfa5a99" in hassfest
    for action, source in (
        ("actions/checkout", workflows),
        ("actions/setup-python", workflows),
        ("actions/upload-artifact", validate),
        ("actions/attest", release),
    ):
        assert re.search(
            rf"uses:\s*{re.escape(action)}@[0-9a-f]{{40}}(?:\s|#|$)",
            source,
        ), f"{action} must be pinned to a full commit SHA"
    assert "tools/check_publication.py --strict" in release
    assert "--draft" in release
    assert "gh release upload" in release
    assert "--draft=false" in release


def test_publication_checker_rejects_mutable_workflow_dependency(tmp_path: Path) -> None:
    target = tmp_path / "repository"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns("dist", ".pytest_cache", "__pycache__", "*.pyc"),
    )
    workflow = target / ".github/workflows/validate.yml"
    text, replacements = re.subn(
        r"actions/checkout@[0-9a-f]{40}",
        "actions/checkout@main",
        workflow.read_text(encoding="utf-8"),
        count=1,
    )
    assert replacements == 1
    workflow.write_text(text, encoding="utf-8")
    result = subprocess.run(
        ["python", str(target / "tools/check_publication.py"), "--root", str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "not pinned to a full commit SHA" in (result.stdout + result.stderr)


def test_brand_assets_exist_at_hacs_and_home_assistant_locations() -> None:
    for name in ("icon.png", "icon@2x.png", "logo.png", "logo@2x.png"):
        repository_asset = ROOT / "brand" / name
        integration_asset = ROOT / "custom_components/portfolio_architect/brand" / name
        assert repository_asset.is_file()
        assert integration_asset.is_file()
        assert repository_asset.read_bytes() == integration_asset.read_bytes()


def test_quality_scale_audit_is_conservative() -> None:
    audit = yaml.safe_load(
        (ROOT / "custom_components/portfolio_architect/quality_scale.yaml").read_text()
    )["rules"]
    assert audit["config-flow"] == "done"
    assert audit["diagnostics"] == "done"
    assert audit["repair-issues"] == "done"
    assert audit["integration-owner"] is None
    assert audit["test-coverage"] is None
    assert audit["strict-typing"] is None
    manifest = json.loads(
        (ROOT / "custom_components/portfolio_architect/manifest.json").read_text()
    )
    assert "quality_scale" not in manifest


def test_python_validation_toolchain_is_exact_and_hash_locked() -> None:
    lockfile = ROOT / "requirements/ci-python-3.14-linux-x86_64.txt"
    expected = {
        "pytest==9.0.3": "2c5efc453d45394fdd706ade797c0a81091eccd1d6e4bccfcd476e2b8e0ab5d9",
        "iniconfig==2.1.0": "9deba5723312380e77435581c6bf4935c94cbfab9b1ed33ef8d238ea168eb760",
        "packaging==25.0": "29572ef2b1f17581046b3a2227d5c611fb25ec70ca1ba8554b24b0e69331a484",
        "pluggy==1.6.0": "e920276dd6813095e9377c0bc5566d94c932c33b27a3e3945d8389c374dd4746",
        "Pygments==2.20.0": "81a9e26dd42fd28a23a2d169d86d7ac03b46e2f8b59ed4698fb4785f946d0176",
        "PyYAML==6.0.3": "c458b6d084f9b935061bc36216e8a69a7e293a2f1e68bf956dcd9e6cbcd143f5",
        "Pillow==12.2.0": "4bfd07bc812fbd20395212969e41931001fd59eb55a60658b0e5710872e95286",
    }
    logical: list[str] = []
    pending = ""
    for raw_line in lockfile.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        continued = line.endswith("\\")
        fragment = line[:-1].strip() if continued else line
        pending = f"{pending} {fragment}".strip()
        if not continued:
            logical.append(pending)
            pending = ""
    assert pending == ""
    assert logical == [
        f"{requirement} --hash=sha256:{digest}"
        for requirement, digest in expected.items()
    ]

    for workflow_name in ("validate.yml", "release.yml"):
        workflow = (ROOT / ".github/workflows" / workflow_name).read_text()
        assert "runs-on: ubuntu-24.04" in workflow
        assert 'python-version: "3.14.6"' in workflow
        assert "--require-hashes" in workflow
        assert "--no-deps" in workflow
        assert "--only-binary=:all:" in workflow
        assert "-r requirements/ci-python-3.14-linux-x86_64.txt" in workflow
        assert "pip install --upgrade" not in workflow.casefold()
        assert workflow.casefold().count("pip install") == 1


def test_publication_checker_rejects_unhashed_python_dependency(tmp_path: Path) -> None:
    target = tmp_path / "repository"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns("dist", ".pytest_cache", "__pycache__", "*.pyc"),
    )
    lockfile = target / "requirements/ci-python-3.14-linux-x86_64.txt"
    text = lockfile.read_text(encoding="utf-8").replace(
        "pytest==9.0.3 \\\n"
        "    --hash=sha256:2c5efc453d45394fdd706ade797c0a81091eccd1d6e4bccfcd476e2b8e0ab5d9",
        "pytest==9.0.3",
        1,
    )
    lockfile.write_text(text, encoding="utf-8")
    result = subprocess.run(
        ["python", str(target / "tools/check_publication.py"), "--root", str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "full SHA-256 hashes" in (result.stdout + result.stderr)


def test_publication_checker_rejects_non_enforcing_pip_install(tmp_path: Path) -> None:
    target = tmp_path / "repository"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns("dist", ".pytest_cache", "__pycache__", "*.pyc"),
    )
    workflow = target / ".github/workflows/validate.yml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8").replace("--require-hashes", "", 1),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["python", str(target / "tools/check_publication.py"), "--root", str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "--require-hashes" in (result.stdout + result.stderr)
