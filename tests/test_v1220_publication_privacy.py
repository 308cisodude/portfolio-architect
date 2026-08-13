"""Regression contracts for v1.22.0 publication/privacy hardening."""

from __future__ import annotations

import importlib.util
import shutil
import sys
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).parents[1]
PRIVACY_PATH = ROOT / "tools/check_privacy.py"
BUILD_PATH = ROOT / "tools/build_release.py"
GITLEAKS_IMAGE = (
    "ghcr.io/gitleaks/gitleaks@sha256:"
    "691af3c7c5a48b16f187ce3446d5f194838f91238f27270ed36eef6359a574d9"
)

spec = importlib.util.spec_from_file_location("portfolio_architect_check_privacy", PRIVACY_PATH)
assert spec is not None and spec.loader is not None
privacy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = privacy
spec.loader.exec_module(privacy)

build_spec = importlib.util.spec_from_file_location("portfolio_architect_build_release", BUILD_PATH)
assert build_spec is not None and build_spec.loader is not None
build_release = importlib.util.module_from_spec(build_spec)
sys.modules[build_spec.name] = build_release
build_spec.loader.exec_module(build_release)


def test_current_source_passes_portfolio_privacy_gate() -> None:
    assert privacy.scan_source(ROOT, ()) == []


def test_valid_iban_is_detected_but_deliberate_invalid_placeholder_is_not() -> None:
    # Build the canonical test value at runtime so a valid IBAN is never committed
    # as one contiguous repository literal.
    valid = "".join(("DE89", "3704", "0044", "0532", "0130", "00"))
    assert privacy.iban_is_valid(valid)
    findings = privacy.text_findings(f'iban: "{valid}"', "synthetic.txt", ())
    assert {item.rule for item in findings} == {"valid-iban"}
    grouped = " ".join((valid[:4], valid[4:8], valid[8:12], valid[12:16], valid[16:20], valid[20:]))
    assert privacy.iban_is_valid(grouped)
    assert any(
        item.rule == "valid-iban"
        for item in privacy.text_findings(f'iban: "{grouped}"', "synthetic.txt", ())
    )

    invalid = "DE00" + "123456789012345678"
    assert not privacy.iban_is_valid(invalid)
    assert not any(
        item.rule == "valid-iban"
        for item in privacy.text_findings(f'accountDisplayId: "{invalid}"', "test.py", ())
    )


def test_private_file_and_fixture_path_policy_is_fail_closed() -> None:
    assert privacy.path_findings("private/statement.pdf")
    assert privacy.path_findings("private/backup.zip")
    assert privacy.path_findings("screenshots/account.svg")
    assert privacy.path_findings("screenshots/account.png")
    assert privacy.path_findings("private/brand/icon.png")
    assert privacy.path_findings("tests/fixtures/new-broker-export.csv")
    assert privacy.path_findings("tests/fixtures/new-broker-payload.json")
    assert privacy.path_findings(".storage/core.config_entries")
    assert privacy.path_findings(".env.local")

    for allowed in (
        "examples/generic-csv/portfolio.csv",
        "tests/fixtures/comdirect-depot-sanitized.csv",
        "tests/fixtures/dkb-depot.csv",
    ):
        assert privacy.path_findings(allowed) == []
        assert (ROOT / allowed).is_file()


def test_provider_identity_values_must_be_unmistakably_synthetic() -> None:
    assert privacy.text_findings('accountId: "ACCOUNT-1"', "fixture.json", ()) == []
    assert privacy.text_findings('account_id="account-internal-1"', "fixture.py", ()) == []
    assert privacy.text_findings('depotNumber: "111111111"', "fixture.json", ()) == []

    non_synthetic = "PRIVATE" + "-ACCOUNT-42"
    findings = privacy.text_findings(
        f'accountId: "{non_synthetic}"', "fixture.json", ()
    )
    assert {item.rule for item in findings} == {"provider-identity-literal"}


def test_exact_private_literals_are_loaded_only_from_outside_repository_and_redacted(
    tmp_path: Path,
) -> None:
    literal = "maintainer-" + "private-marker"
    literal_file = tmp_path / "private-literals.txt"
    literal_file.write_text(literal + "\n", encoding="utf-8")
    values = privacy.load_private_literals(ROOT, literal_file)
    assert values == (literal,)

    findings = privacy.text_findings(f"prefix {literal} suffix", "candidate.txt", values)
    rendered = "\n".join(item.render() for item in findings)
    assert "known-private-literal-1" in rendered
    assert literal not in rendered

    inside = ROOT / ".privacy-literals-test"
    try:
        inside.write_text(literal, encoding="utf-8")
        try:
            privacy.load_private_literals(ROOT, inside)
        except SystemExit as err:
            assert "outside the repository" in str(err)
        else:
            raise AssertionError("repository-local private literal file must be rejected")
    finally:
        inside.unlink(missing_ok=True)


def test_complete_git_history_catches_deleted_private_material(tmp_path: Path) -> None:
    repository = tmp_path / "history-repository"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Synthetic Maintainer"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "synthetic@example.invalid"], cwd=repository, check=True)

    valid = "".join(("DE89", "3704", "0044", "0532", "0130", "00"))
    leaked_id = "PRIVATE" + "-ACCOUNT-42"
    leaked = repository / "temporary.txt"
    leaked.write_text(f'accountId: "{leaked_id}"\niban: "{valid}"\n', encoding="utf-8")
    statement = repository / "statement.pdf"
    statement.write_bytes(b"synthetic historical binary")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "temporary synthetic leak"], cwd=repository, check=True)

    leaked.unlink()
    statement.unlink()
    (repository / "README.md").write_text("clean current tree\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "remove temporary material"], cwd=repository, check=True)

    assert privacy.scan_source(repository, ()) == []
    findings = privacy.scan_history(repository, ())
    rules = {item.rule for item in findings}
    assert "valid-iban" in rules
    assert "provider-identity-literal" in rules
    assert "forbidden-private-filetype" in rules


def test_source_scan_rejects_symlinks(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("private external target", encoding="utf-8")
    link = root / "linked.txt"
    try:
        link.symlink_to(target)
    except OSError:
        return
    findings = privacy.scan_source(root, ())
    assert any(item.rule == "forbidden-symlink" for item in findings)


def test_release_builder_excludes_virtualenvs_and_rejects_symlinks(tmp_path: Path) -> None:
    assert ".venv" in build_release.EXCLUDED_PARTS
    assert "venv" in build_release.EXCLUDED_PARTS
    root = tmp_path / "source"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    link = root / "linked.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        return
    try:
        build_release.reject_source_symlinks(root)
    except SystemExit as err:
        assert "must not contain symlinks" in str(err)
    else:
        raise AssertionError("release builder must reject source symlinks")


def test_release_zip_scan_rejects_private_file_and_valid_iban(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    archive = dist / "candidate.zip"
    valid = "".join(("DE89", "3704", "0044", "0532", "0130", "00"))
    with zipfile.ZipFile(archive, "w") as target:
        target.writestr("private/statement.pdf", b"synthetic test document")
        target.writestr("payload.txt", f"iban={valid}\n")

    findings = privacy.scan_dist(dist, ())
    rules = {item.rule for item in findings}
    assert "forbidden-private-filetype" in rules
    assert "valid-iban" in rules


def test_gitleaks_gate_is_immutable_complete_and_prepublication() -> None:
    validate = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    runner_path = ROOT / "tools/run_gitleaks_ci.sh"
    runner = runner_path.read_text(encoding="utf-8")
    assert runner.startswith("#!/usr/bin/env bash")

    assert "fetch-depth: 0" in validate
    assert GITLEAKS_IMAGE in validate
    assert GITLEAKS_IMAGE in release
    assert GITLEAKS_IMAGE in runner
    assert "v8.30.1" not in runner
    assert "git log -p --all --no-ext-diff --text -- ." in runner
    assert "set -euo pipefail" in runner
    assert "git rev-list --all --count" in runner
    assert "git archive --format=tar HEAD" in runner
    assert "--history" in runner
    assert runner.count("--network=none") == 3
    assert runner.count("--cap-drop=ALL") == 3
    assert runner.count("--security-opt=no-new-privileges") == 3

    scan = release.index("bash tools/run_gitleaks_ci.sh dist")
    assert scan < release.index("uses: actions/attest@")
    assert scan < release.index("gh release create")


def test_release_pipeline_runs_privacy_gate_before_and_after_build() -> None:
    release_check = (ROOT / "tools/release_check.sh").read_text(encoding="utf-8")
    pre = release_check.index("python tools/check_privacy.py --root .")
    build = release_check.index("python tools/build_release.py --output dist")
    post = release_check.index("python tools/check_privacy.py --root . --dist dist")
    assert pre < build < post


def test_publication_checker_rejects_changed_gitleaks_digest(tmp_path: Path) -> None:
    target = tmp_path / "repository"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns("dist", ".pytest_cache", "__pycache__", "*.pyc"),
    )
    workflow = target / ".github/workflows/validate.yml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8").replace(
            GITLEAKS_IMAGE,
            "ghcr.io/gitleaks/gitleaks@sha256:" + "0" * 64,
            1,
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["python", str(target / "tools/check_publication.py"), "--root", str(target)],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "reviewed Gitleaks image" in (result.stdout + result.stderr)


def test_roadmap_orders_provider_gateways_before_trade_republic_import() -> None:
    roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
    gateway = roadmap.index("distinct provider Gateway Apps")
    section = roadmap[gateway:]
    comdirect = section.index("Gateway — Comdirect")
    dkb = section.index("Gateway — DKB")
    trade_republic = section.index("Gateway — Trade Republic")
    statement_import = section.index("Trade Republic statement import")
    assert comdirect < dkb < trade_republic < statement_import
    assert "real Trade Republic statements remain private input" in roadmap
    assert "wholly synthetic documents/fixtures only" in roadmap
