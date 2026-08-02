#!/usr/bin/env python3
"""Verify Portfolio Architect release artifacts and archive safety."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum_file(directory: Path) -> None:
    checksum_file = directory / "SHA256SUMS"
    if not checksum_file.is_file():
        raise SystemExit(f"Missing {checksum_file}")
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, name = line.split("  ", 1)
        target = directory / name
        if not target.is_file():
            raise SystemExit(f"Checksum target missing: {name}")
        actual = sha256(target)
        if actual != expected:
            raise SystemExit(f"Checksum mismatch for {name}: {actual} != {expected}")


def verify_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        seen: set[str] = set()
        for info in archive.infolist():
            member = PurePosixPath(info.filename)
            if member.is_absolute() or ".." in member.parts:
                raise SystemExit(f"Unsafe ZIP member in {path.name}: {info.filename}")
            if info.filename in seen:
                raise SystemExit(f"Duplicate ZIP member in {path.name}: {info.filename}")
            seen.add(info.filename)
            if info.is_dir():
                continue
            archive.read(info)
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"Corrupt ZIP member in {path.name}: {bad}")


def version() -> str:
    return str(
        json.loads(
            (PROJECT_ROOT / "custom_components/portfolio_architect/manifest.json").read_text()
        )["version"]
    )


def verify_expected_files(directory: Path, release_version: str) -> None:
    expected = {
        f"portfolio-architect-v{release_version}-ha-dropin.zip",
        "portfolio_architect.zip",
        f"portfolio-architect-gateway-app-v{release_version}.zip",
        f"portfolio-architect-v{release_version}.zip",
        f"portfolio-architect-v{release_version}-bilingual-dashboard.yaml",
        f"portfolio-architect-v{release_version}-upgrade-guide.md",
        f"portfolio-architect-v{release_version}-release-notes.md",
        f"portfolio-architect-v{release_version}-sbom.spdx.json",
        "SHA256SUMS",
    }
    missing = sorted(name for name in expected if not (directory / name).is_file())
    if missing:
        raise SystemExit(f"Missing release artifacts: {missing}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=PROJECT_ROOT / "dist")
    args = parser.parse_args()
    dist = args.dist.resolve()
    release_version = version()
    verify_expected_files(dist, release_version)
    verify_checksum_file(dist)
    for archive in sorted(dist.glob("*.zip")):
        verify_zip(archive)
    sbom = json.loads(
        (dist / f"portfolio-architect-v{release_version}-sbom.spdx.json").read_text()
    )
    if sbom.get("spdxVersion") != "SPDX-2.3":
        raise SystemExit("SBOM is not SPDX 2.3")
    if not re.fullmatch(r"\d+\.\d+\.\d+", release_version):
        raise SystemExit(f"Unexpected release version: {release_version}")
    print(f"Verified Portfolio Architect v{release_version} release in {dist}")


if __name__ == "__main__":
    main()
