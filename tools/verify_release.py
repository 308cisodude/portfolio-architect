#!/usr/bin/env python3
"""Verify Portfolio Architect release artifacts and archive safety."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile

import yaml
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


def archive_payload(path: Path, prefix: str = "") -> dict[str, str]:
    """Return normalized file SHA-256 values from an archive."""
    payload: dict[str, str] = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if prefix:
                if not name.startswith(prefix):
                    raise SystemExit(
                        f"Unexpected member outside {prefix} in {path.name}: {name}"
                    )
                name = name[len(prefix) :]
            if not name:
                raise SystemExit(f"Empty normalized member name in {path.name}")
            payload[name] = hashlib.sha256(archive.read(info)).hexdigest()
    return payload


def verify_integration_archive_layouts(directory: Path, release_version: str) -> None:
    """Verify the distinct HACS and manual extraction boundaries."""
    hacs_path = directory / "portfolio_architect.zip"
    dropin_path = directory / f"portfolio-architect-v{release_version}-ha-dropin.zip"
    dropin_prefix = "custom_components/portfolio_architect/"

    hacs_payload = archive_payload(hacs_path)
    dropin_payload = archive_payload(dropin_path, prefix=dropin_prefix)

    required_hacs = {
        "__init__.py",
        "manifest.json",
        "const.py",
        "engine/__init__.py",
        "brand/icon.png",
    }
    nested_hacs = sorted(
        name for name in hacs_payload if name.startswith("custom_components/")
    )
    if nested_hacs:
        raise SystemExit(
            "HACS archive must not contain a custom_components/ prefix; "
            f"found {nested_hacs[0]}"
        )
    missing_hacs = sorted(required_hacs - hacs_payload.keys())
    if missing_hacs:
        raise SystemExit(
            f"HACS archive is missing root-level integration files: {missing_hacs}"
        )

    with zipfile.ZipFile(dropin_path) as archive:
        dropin_names = {info.filename for info in archive.infolist() if not info.is_dir()}
    expected_manifest = f"{dropin_prefix}manifest.json"
    if expected_manifest not in dropin_names:
        raise SystemExit(
            "Manual drop-in is missing the custom_components/portfolio_architect wrapper"
        )
    if "manifest.json" in dropin_names:
        raise SystemExit("Manual drop-in unexpectedly contains a root-level manifest.json")

    if hacs_payload != dropin_payload:
        only_hacs = sorted(hacs_payload.keys() - dropin_payload.keys())
        only_dropin = sorted(dropin_payload.keys() - hacs_payload.keys())
        changed = sorted(
            name
            for name in hacs_payload.keys() & dropin_payload.keys()
            if hacs_payload[name] != dropin_payload[name]
        )
        raise SystemExit(
            "HACS and manual drop-in payloads differ after prefix normalization: "
            f"only_hacs={only_hacs}, only_dropin={only_dropin}, changed={changed}"
        )

    with zipfile.ZipFile(hacs_path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    if str(manifest.get("version")) != release_version:
        raise SystemExit(
            f"HACS manifest version {manifest.get('version')} != {release_version}"
        )



def verify_gateway_app_archive_layouts(directory: Path, release_version: str) -> None:
    """Verify provider App identity, archive roots, and shell isolation."""
    specs = {
        "portfolio-architect-gateway-comdirect-app-v%s.zip" % release_version: (
            "portfolio_architect_gateway_comdirect",
            "portfolio_architect_gateway_comdirect",
            "stable",
            None,
            "auto",
        ),
        "portfolio-architect-gateway-dkb-app-v%s.zip" % release_version: (
            "portfolio_architect_gateway_dkb",
            "portfolio_architect_gateway_dkb",
            "stable",
            "dkb",
            "auto",
        ),
        "portfolio-architect-gateway-trade-republic-app-v%s.zip" % release_version: (
            "portfolio_architect_gateway_trade_republic",
            "portfolio_architect_gateway_trade_republic",
            "stable",
            "trade_republic",
            "auto",
        ),
        "portfolio-architect-gateway-import-app-v%s.zip" % release_version: (
            "portfolio_architect_gateway_import",
            "portfolio_architect_gateway_import",
            "stable",
            "generic_csv",
            "auto",
        ),
    }
    for archive_name, (root, slug, stage, provider_id, expected_boot) in specs.items():
        path = directory / archive_name
        prefix = f"{root}/"
        payload = archive_payload(path, prefix=prefix)
        required = {"config.yaml", "Dockerfile", "entrypoint.py", "SHA256SUMS"}
        missing = sorted(required - payload.keys())
        if missing:
            raise SystemExit(f"{archive_name} missing App files: {missing}")
        with zipfile.ZipFile(path) as archive:
            config = yaml.safe_load(archive.read(prefix + "config.yaml"))
        if str(config.get("version")) != release_version:
            raise SystemExit(f"{archive_name} version is not {release_version}")
        if config.get("slug") != slug:
            raise SystemExit(f"{archive_name} slug mismatch: {config.get('slug')}")
        if config.get("stage") != stage:
            raise SystemExit(f"{archive_name} stage mismatch: {config.get('stage')}")
        if config.get("boot", "auto") != expected_boot:
            raise SystemExit(f"{archive_name} boot policy mismatch")
        if provider_id is not None:
            if config.get("environment", {}).get("PA_PROVIDER_ID") != provider_id:
                raise SystemExit(f"{archive_name} provider identity mismatch")
            forbidden = {
                "src/portfolio_architect_gateway/comdirect.py",
                "src/portfolio_architect_gateway/transport.py",
                "src/portfolio_architect_gateway/cash_policy.py",
                "src/portfolio_architect_gateway/app.py",
                "src/portfolio_architect_gateway/config.py",
            }
            leaked = sorted(forbidden & payload.keys())
            if leaked:
                raise SystemExit(
                    f"{archive_name} contains provider-specific Comdirect modules: {leaked}"
                )
            if provider_id == "dkb":
                for name in (
                    "src/portfolio_architect_gateway/dkb_app.py",
                    "src/portfolio_architect_gateway/dkb_csv.py",
                    "src/portfolio_architect_gateway/dkb_fints.py",
                ):
                    if name not in payload:
                        raise SystemExit(f"{archive_name} missing provider module: {name}")
            if provider_id == "generic_csv":
                for name in (
                    "src/portfolio_architect_gateway/generic_import_app.py",
                    "src/portfolio_architect_gateway/generic_csv.py",
                ):
                    if name not in payload:
                        raise SystemExit(f"{archive_name} missing provider module: {name}")
            if provider_id == "trade_republic":
                dependency = payload.get("requirements.txt")
                if dependency is None:
                    raise SystemExit(f"{archive_name} missing Trade Republic dependency lock")
                required_lock = (PROJECT_ROOT / "home_assistant_app" / "portfolio_architect_gateway_trade_republic" / "requirements.txt").read_bytes()
                if dependency != hashlib.sha256(required_lock).hexdigest():
                    raise SystemExit(f"{archive_name} Trade Republic dependency lock mismatch")
                for name in (
                    "src/portfolio_architect_gateway/trade_republic_app.py",
                    "src/portfolio_architect_gateway/trade_republic_statement.py",
                    "src/portfolio_architect_gateway/trade_republic_cash_statement.py",
                    "src/portfolio_architect_gateway/trade_republic_pdf.py",
                ):
                    if name not in payload:
                        raise SystemExit(f"{archive_name} missing provider module: {name}")
            elif "requirements.txt" in payload:
                raise SystemExit(f"{archive_name} unexpectedly contains provider dependency lock")

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
        f"portfolio-architect-gateway-comdirect-app-v{release_version}.zip",
        f"portfolio-architect-gateway-dkb-app-v{release_version}.zip",
        f"portfolio-architect-gateway-trade-republic-app-v{release_version}.zip",
        f"portfolio-architect-gateway-import-app-v{release_version}.zip",
        f"portfolio-architect-v{release_version}.zip",
        f"portfolio-architect-v{release_version}-dashboard-en.yaml",
        f"portfolio-architect-v{release_version}-dashboard-de.yaml",
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
    verify_integration_archive_layouts(dist, release_version)
    verify_gateway_app_archive_layouts(dist, release_version)
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
