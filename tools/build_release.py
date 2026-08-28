#!/usr/bin/env python3
"""Build reproducible Portfolio Architect release archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".pytest_cache", "__pycache__", "dist", ".venv", "venv"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
EXCLUDED_ROOT_FILES = {"PACKAGE-MANIFEST.json", "SHA256SUMS"}
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def include_path(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return False
    if len(relative.parts) == 1 and relative.name in EXCLUDED_ROOT_FILES:
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def source_files() -> list[Path]:
    return sorted(
        (path for path in PROJECT_ROOT.rglob("*") if include_path(path)),
        key=lambda item: item.relative_to(PROJECT_ROOT).as_posix(),
    )


def reject_source_symlinks(root: Path = PROJECT_ROOT) -> None:
    """Refuse release staging through filesystem links outside the source tree."""
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.is_symlink():
            raise SystemExit(f"Release source must not contain symlinks: {relative.as_posix()}")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def package_manifest(root: Path) -> dict[str, object]:
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in {"PACKAGE-MANIFEST.json", "SHA256SUMS"}:
            continue
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }
        )
    return {"schema": 1, "files": files}


def write_checksums(root: Path, destination: Path) -> None:
    lines = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == destination:
            continue
        lines.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def normalized_mode(path: Path) -> int:
    executable = bool(path.stat().st_mode & stat.S_IXUSR)
    return 0o755 if executable else 0o644


def write_reproducible_zip(source_root: Path, archive: Path, prefix: str = "") -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        for path in sorted(source_root.rglob("*")):
            if not path.is_file():
                continue
            relative = PurePosixPath(path.relative_to(source_root).as_posix())
            member = PurePosixPath(prefix) / relative if prefix else relative
            info = zipfile.ZipInfo(member.as_posix(), date_time=ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = normalized_mode(path) << 16
            info.create_system = 3
            target.writestr(info, path.read_bytes())


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache"),
    )


def read_version() -> str:
    manifest = json.loads(
        (PROJECT_ROOT / "custom_components/portfolio_architect/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    return str(manifest["version"])


def validate_version(version: str) -> None:
    expected = {
        "integration": json.loads(
            (PROJECT_ROOT / "custom_components/portfolio_architect/manifest.json").read_text()
        )["version"],
        "gateway_comdirect_legacy": __import__("yaml").safe_load((PROJECT_ROOT / "home_assistant_app/portfolio_architect_gateway/config.yaml").read_text())["version"],
        "gateway_comdirect": __import__("yaml").safe_load((PROJECT_ROOT / "home_assistant_app/portfolio_architect_gateway_comdirect/config.yaml").read_text())["version"],
        "gateway_dkb": __import__("yaml").safe_load((PROJECT_ROOT / "home_assistant_app/portfolio_architect_gateway_dkb/config.yaml").read_text())["version"],
        "gateway_trade_republic": __import__("yaml").safe_load((PROJECT_ROOT / "home_assistant_app/portfolio_architect_gateway_trade_republic/config.yaml").read_text())["version"],
        "gateway_import": __import__("yaml").safe_load((PROJECT_ROOT / "home_assistant_app/portfolio_architect_gateway_import/config.yaml").read_text())["version"],
    }
    mismatches = {name: value for name, value in expected.items() if str(value) != version}
    if mismatches:
        raise SystemExit(f"Version mismatch: expected {version}, found {mismatches}")


def build(output: Path) -> list[Path]:
    reject_source_symlinks()
    version = read_version()
    validate_version(version)
    output = output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    with tempfile.TemporaryDirectory(prefix="portfolio-architect-release-") as temp_name:
        temp = Path(temp_name)

        # Manual Home Assistant drop-in. It is extracted over /config and must
        # therefore retain the custom_components/portfolio_architect wrapper.
        dropin_stage = temp / "dropin"
        copy_tree(PROJECT_ROOT / "custom_components", dropin_stage / "custom_components")
        integration_archive = output / f"portfolio-architect-v{version}-ha-dropin.zip"
        write_reproducible_zip(dropin_stage, integration_archive)

        # Stable HACS release asset. HACS already extracts into
        # /config/custom_components/portfolio_architect, so the integration files
        # must be placed directly at the archive root. This archive is deliberately
        # not byte-identical to the manual drop-in.
        hacs_stage = temp / "hacs"
        copy_tree(
            PROJECT_ROOT / "custom_components/portfolio_architect",
            hacs_stage,
        )
        hacs_archive = output / "portfolio_architect.zip"
        write_reproducible_zip(hacs_stage, hacs_archive)

        # Home Assistant provider Gateway Apps. Keep the historical Comdirect asset
        # during the explicit v1.55 identity migration and publish the provider-qualified
        # successor as a separate package.
        app_specs = (
            ("portfolio_architect_gateway", f"portfolio-architect-gateway-app-v{version}.zip"),
            ("portfolio_architect_gateway_comdirect", f"portfolio-architect-gateway-comdirect-app-v{version}.zip"),
            ("portfolio_architect_gateway_dkb", f"portfolio-architect-gateway-dkb-app-v{version}.zip"),
            ("portfolio_architect_gateway_trade_republic", f"portfolio-architect-gateway-trade-republic-app-v{version}.zip"),
            ("portfolio_architect_gateway_import", f"portfolio-architect-gateway-import-app-v{version}.zip"),
        )
        for app_dir, archive_name in app_specs:
            app_temp = temp / f"app-{app_dir}"
            app_stage = app_temp / app_dir
            copy_tree(PROJECT_ROOT / "home_assistant_app" / app_dir, app_stage)
            write_checksums(app_stage, app_stage / "SHA256SUMS")
            write_reproducible_zip(app_temp, output / archive_name)

        # Complete source release with generated manifest and checksums.
        full_stage = temp / f"portfolio-architect-v{version}"
        for path in source_files():
            destination = full_stage / path.relative_to(PROJECT_ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        write_json(full_stage / "PACKAGE-MANIFEST.json", package_manifest(full_stage))
        write_checksums(full_stage, full_stage / "SHA256SUMS")
        full_archive = output / f"portfolio-architect-v{version}.zip"
        write_reproducible_zip(full_stage, full_archive, prefix=full_stage.name)

        # Convenience files published beside the archives.
        copies = {
            PROJECT_ROOT / "dashboard/bilingual-dashboard.yaml": output
            / f"portfolio-architect-v{version}-bilingual-dashboard.yaml",
            PROJECT_ROOT / f"docs/UPGRADE-{version}.md": output
            / f"portfolio-architect-v{version}-upgrade-guide.md",
            PROJECT_ROOT / "docs/RELEASE-NOTES.md": output
            / f"portfolio-architect-v{version}-release-notes.md",
            PROJECT_ROOT / "SBOM.spdx.json": output / f"portfolio-architect-v{version}-sbom.spdx.json",
        }
        for source, destination in copies.items():
            shutil.copy2(source, destination)

    artifacts = sorted(path for path in output.iterdir() if path.is_file())
    checksum_path = output / "SHA256SUMS"
    checksum_lines = [
        f"{sha256(path)}  {path.name}" for path in artifacts if path != checksum_path
    ]
    checksum_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return sorted(path for path in output.iterdir() if path.is_file())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "dist")
    args = parser.parse_args()
    artifacts = build(args.output)
    for path in artifacts:
        print(f"{sha256(path)}  {path.name}")


if __name__ == "__main__":
    main()
