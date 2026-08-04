#!/usr/bin/env python3
"""Validate Portfolio Architect publication metadata and repository contracts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CODEOWNER_RE = re.compile(r"^@[A-Za-z0-9-]+$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-(?:rc|beta|alpha)\d+)?$")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
IMAGE_DIGEST_RE = re.compile(r"ghcr\.io/[A-Za-z0-9_.\/-]+@sha256:[0-9a-f]{64}")
ACTION_REF_RE = re.compile(r"^\s*-?\s*uses:\s*[^@\s]+@([^\s#]+)", re.MULTILINE)
LOCKFILE_RELATIVE = Path("requirements/ci-python-3.14-linux-x86_64.txt")
LOCKED_PYTHON_WORKFLOWS = ("validate.yml", "release.yml")
LOCKED_RUNNER = "ubuntu-24.04"
LOCKED_PYTHON = "3.14.6"
REQUIREMENT_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[^\s\\]+)"
    r"(?P<hashes>(?:\s+--hash=sha256:[0-9a-f]{64})+)$"
)


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)



def validate_immutable_workflow_dependencies(root: Path) -> None:
    """Reject mutable GitHub Action and container-image references."""
    for workflow in sorted((root / ".github/workflows").glob("*.yml")):
        text = workflow.read_text(encoding="utf-8")
        for reference in ACTION_REF_RE.findall(text):
            require(
                FULL_SHA_RE.fullmatch(reference) is not None,
                f"Workflow action is not pinned to a full commit SHA: {workflow.name} @{reference}",
            )
        for line in text.splitlines():
            if "ghcr.io/" not in line:
                continue
            require(
                IMAGE_DIGEST_RE.search(line) is not None,
                f"Workflow container is not pinned to a SHA-256 digest: {workflow.name}",
            )
        require("@main" not in text, f"Mutable @main reference in {workflow.name}")
        require("@master" not in text, f"Mutable @master reference in {workflow.name}")
        require(":latest" not in text, f"Mutable :latest image in {workflow.name}")
        require(
            "runs-on: ubuntu-latest" not in text,
            f"Floating ubuntu-latest runner in {workflow.name}",
        )


def _logical_requirement_lines(path: Path) -> list[str]:
    """Return non-comment requirement entries with continuations joined."""
    entries: list[str] = []
    pending = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        continued = line.endswith("\\")
        fragment = line[:-1].strip() if continued else line
        pending = f"{pending} {fragment}".strip()
        if not continued:
            entries.append(pending)
            pending = ""
    require(not pending, f"Unterminated requirement continuation in {path}")
    return entries


def validate_hash_locked_python_toolchain(root: Path) -> None:
    """Validate the exact, hash-locked Python toolchain used by CI and releases."""
    lockfile = root / LOCKFILE_RELATIVE
    require(lockfile.is_file(), f"Missing Python dependency lock: {LOCKFILE_RELATIVE}")
    entries = _logical_requirement_lines(lockfile)
    require(bool(entries), f"Python dependency lock is empty: {LOCKFILE_RELATIVE}")

    packages: set[str] = set()
    for entry in entries:
        match = REQUIREMENT_RE.fullmatch(entry)
        require(
            match is not None,
            "Every locked Python dependency must use NAME==VERSION and one or "
            f"more full SHA-256 hashes: {entry}",
        )
        name = match.group("name").replace("_", "-").casefold()
        require(name not in packages, f"Duplicate locked Python dependency: {name}")
        packages.add(name)

    for required in ("pytest", "pyyaml", "pillow"):
        require(required in packages, f"Missing required validation dependency: {required}")

    for workflow_name in LOCKED_PYTHON_WORKFLOWS:
        workflow = root / ".github/workflows" / workflow_name
        text = workflow.read_text(encoding="utf-8")
        lower = text.casefold()
        require(
            f"runs-on: {LOCKED_RUNNER}" in text,
            f"{workflow_name} must pin the runner to {LOCKED_RUNNER}",
        )
        require(
            f'python-version: "{LOCKED_PYTHON}"' in text,
            f"{workflow_name} must pin Python to {LOCKED_PYTHON}",
        )
        for token in (
            "--require-hashes",
            "--no-deps",
            "--only-binary=:all:",
            f"-r {LOCKFILE_RELATIVE.as_posix()}",
        ):
            require(token in text, f"{workflow_name} is missing locked-install option: {token}")
        require(
            lower.count("pip install") == 1,
            f"{workflow_name} must contain exactly one reviewed pip install command",
        )
        require(
            "pip install --upgrade" not in lower and "pip install -u" not in lower,
            f"{workflow_name} must not perform an unbounded pip upgrade",
        )


def validate(root: Path, strict: bool) -> None:
    manifest = read_json(root / "custom_components/portfolio_architect/manifest.json")
    hacs = read_json(root / "hacs.json")
    publication = read_json(root / "publication.json")

    require(manifest.get("domain") == "portfolio_architect", "Unexpected integration domain")
    require(SEMVER_RE.fullmatch(str(manifest.get("version", ""))) is not None, "Invalid version")
    require(manifest.get("config_flow") is True, "Config flow must remain enabled")
    require(manifest.get("single_config_entry") is True, "Single-entry contract missing")

    require(hacs.get("name") == "Portfolio Architect", "Unexpected HACS name")
    require(hacs.get("zip_release") is True, "HACS must consume a release ZIP")
    require(hacs.get("filename") == "portfolio_architect.zip", "Unexpected HACS filename")
    require(hacs.get("homeassistant") == "2026.7.0", "Unexpected Home Assistant floor")

    required_files = [
        "README.md",
        "LICENSE",
        "SECURITY.md",
        "SUPPORT.md",
        "CONTRIBUTING.md",
        "brand/icon.png",
        "custom_components/portfolio_architect/brand/icon.png",
        "custom_components/portfolio_architect/quality_scale.yaml",
        ".github/workflows/validate.yml",
        ".github/workflows/hacs.yml",
        ".github/workflows/hassfest.yml",
        ".github/workflows/release.yml",
        ".github/dependabot.yml",
        "requirements/ci-python-3.14-linux-x86_64.txt",
        "docs/PUBLISHING.md",
        "docs/SUPPORTED-VERSIONS.md",
        "docs/QUALITY-SCALE-AUDIT.md",
    ]
    for relative in required_files:
        require((root / relative).is_file(), f"Missing publication file: {relative}")

    validate_immutable_workflow_dependencies(root)
    validate_hash_locked_python_toolchain(root)

    if not strict:
        return

    require(publication.get("configured") is True, "Publication metadata is not configured")
    repository = str(publication.get("github_repository", ""))
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) is not None,
            "Invalid GitHub repository metadata")
    codeowners = publication.get("codeowners")
    require(isinstance(codeowners, list) and bool(codeowners), "At least one code owner is required")
    require(all(isinstance(value, str) and CODEOWNER_RE.fullmatch(value) for value in codeowners),
            "Invalid code owner")
    base = f"https://github.com/{repository}"
    require(manifest.get("documentation") == f"{base}#readme", "Documentation URL mismatch")
    require(manifest.get("issue_tracker") == f"{base}/issues", "Issue tracker URL mismatch")
    require(manifest.get("codeowners") == codeowners, "Manifest code owners mismatch")
    codeowners_file = root / ".github/CODEOWNERS"
    require(codeowners_file.is_file(), "Missing configured CODEOWNERS file")
    require(
        not (root / ".github/CODEOWNERS.example").exists(),
        "Remove CODEOWNERS.example after creating the active CODEOWNERS file",
    )
    for generated_name in ("PACKAGE-MANIFEST.json", "SHA256SUMS"):
        require(
            not (root / generated_name).exists(),
            f"Remove source-release transport metadata before publication: {generated_name}",
        )
    text = codeowners_file.read_text(encoding="utf-8")
    require(all(owner in text for owner in codeowners), "CODEOWNERS content mismatch")
    for protected_path in (
        "*",
        "/.github/workflows/",
        "/.github/dependabot.yml",
        "/tools/configure_publication.py",
        "/tools/check_publication.py",
        "/tools/release_check.sh",
        "/custom_components/portfolio_architect/",
        "/home_assistant_app/portfolio_architect_gateway/",
        "/gateway/",
    ):
        require(
            any(line.startswith(f"{protected_path} ") for line in text.splitlines()),
            f"CODEOWNERS does not explicitly protect {protected_path}",
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    validate(args.root.resolve(), args.strict)
    mode = "strict public" if args.strict else "local publication-readiness"
    print(f"Validated {mode} contracts")


if __name__ == "__main__":
    main()
