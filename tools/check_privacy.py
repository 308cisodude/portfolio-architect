#!/usr/bin/env python3
"""Fail-closed privacy and publication-hygiene checks for Portfolio Architect.

The public repository may contain source code, public security identifiers, generic
provider names, and wholly synthetic fixtures. It must not contain attributable
bank/account data, credentials, raw broker documents, or accidental private files.

This checker deliberately complements (rather than replaces) a general secret
scanner such as Gitleaks. It understands Portfolio Architect-specific publication
boundaries and safely inspects both the source tree and release ZIP contents.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator

MAX_TEXT_BYTES = 8 * 1024 * 1024
EXCLUDED_DIRS = {".git", ".pytest_cache", "__pycache__", "dist", ".venv", "venv"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
FORBIDDEN_PATH_PARTS = {".storage", "secrets", "backups"}

# Raw documents, backups, databases, key containers, and screenshots are never
# publication inputs. PNG is handled separately because branding is intentional.
FORBIDDEN_SUFFIXES = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ods",
    ".zip",
    ".7z",
    ".rar",
    ".tar",
    ".tgz",
    ".gz",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".kdbx",
    ".log",
    ".bak",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".heic",
    ".avif",
    ".svg",
}

FORBIDDEN_BASENAMES = {
    ".env",
    "secrets.yaml",
    "secrets.yml",
    "credentials.json",
    "credentials.yaml",
    "credentials.yml",
    "id_rsa",
    "id_ed25519",
}

ALLOWED_PRIVATEISH_PATHS = {
    "gateway/.env.example",
    "gateway/secrets/README.md",
}

ALLOWED_CSV_PATHS = {
    "examples/generic-csv/portfolio.csv",
    "tests/fixtures/comdirect-depot-sanitized.csv",
    "tests/fixtures/dkb-depot.csv",
}

ALLOWED_IMAGE_NAMES = {
    "icon.png",
    "icon@2x.png",
    "logo.png",
    "logo@2x.png",
    "dark_icon.png",
    "dark_icon@2x.png",
    "dark_logo.png",
    "dark_logo@2x.png",
}

PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
# Candidate IBANs are validated with the ISO 13616 mod-97 checksum below. Public
# ISINs do not match because they are only 12 characters long.
IBAN_CANDIDATE_RE = re.compile(
    r"(?<![A-Z0-9])([A-Z]{2}\d{2}(?: ?[A-Z0-9]){11,30})(?![A-Z0-9])"
)

# Identity-bearing provider fields are allowed only with unmistakably synthetic
# placeholders. This catches accidental pasted payloads without pretending that
# every arbitrary integer is personal data.
IDENTITY_FIELD_RE = re.compile(
    r"(?ix)\b("
    r"depot[_-]?(?:nummer|number|nr|id)?|"
    r"account[_-]?(?:id|display[_-]?id|number)?|"
    r"customer[_-]?(?:id|number)?|kundennummer|"
    r"portfolio[_-]?(?:id|number)|"
    r"client[_-]?(?:id)?"
    r")\b\s*[\"']?\s*[:=]\s*[\"']([^\"'\r\n]{1,128})[\"']"
)

# Identity/attribution fields copied from provider documents are never public
# fixtures unless their value is unmistakably synthetic. Restrict this pattern to
# quoted mapping keys so ordinary source-code variables such as ``address`` do not
# become false positives.
ATTRIBUTION_FIELD_RE = re.compile(
    r"(?ix)[\"']("
    r"account[_-]?holder|holder[_-]?name|owner[_-]?name|customer[_-]?name|"
    r"tax[_-]?(?:id|number)|steuer[_-]?(?:id|nummer)|postal[_-]?code|"
    r"street|email|phone|telephone"
    r")[\"']\s*:\s*[\"']([^\"'\r\n]{1,160})[\"']"
)

SYNTHETIC_VALUE_RES = (
    re.compile(r"(?i)^(?:ANONYMIZED|REDACTED|DEMO|EXAMPLE|TEST|PLACEHOLDER|SYNTHETIC)$"),
    re.compile(r"(?i)^(?:ACCOUNT|CARD|DEPOT|CUSTOMER|CLIENT)-\d+$"),
    re.compile(r"(?i)^client(?:-id)?$"),
    re.compile(r"(?i)^account-internal-\d+$"),
    re.compile(r"(?i)^D\d+$"),
    re.compile(r"^([0129])\1{3,}$"),
    # Deliberately invalid IBAN check digits used by gateway tests.
    re.compile(r"^DE00[A-Z0-9]{18}$"),
)


@dataclass(frozen=True)
class Finding:
    rule: str
    location: str
    line: int | None = None

    def render(self) -> str:
        suffix = f":{self.line}" if self.line is not None else ""
        return f"{self.rule}: {self.location}{suffix}"


def normalize_member_path(value: str) -> str:
    """Normalize a repository or ZIP-member path for policy matching."""
    path = PurePosixPath(value.replace("\\", "/"))
    parts = list(path.parts)
    if parts and re.fullmatch(r"portfolio-architect-v\d+\.\d+\.\d+", parts[0]):
        parts = parts[1:]
    return PurePosixPath(*parts).as_posix()


def is_allowed_png(relative: str) -> bool:
    path = PurePosixPath(relative)
    if path.name not in ALLOWED_IMAGE_NAMES:
        return False
    parent = path.parent.as_posix()
    if parent in {"brand", "custom_components/portfolio_architect/brand"}:
        return True
    # The Home Assistant Gateway App release stages these two branding files at
    # ``portfolio_architect_gateway/``; the source tree stores them under the App
    # package directory. No arbitrary directory named ``brand`` is trusted.
    if path.name not in {"icon.png", "logo.png"}:
        return False
    return parent in {
        "portfolio_architect_gateway",
        "portfolio_architect_gateway_comdirect",
        "portfolio_architect_gateway_dkb",
        "portfolio_architect_gateway_trade_republic",
        "portfolio_architect_gateway_import",
        "home_assistant_app/portfolio_architect_gateway",
        "home_assistant_app/portfolio_architect_gateway_comdirect",
        "home_assistant_app/portfolio_architect_gateway_dkb",
        "home_assistant_app/portfolio_architect_gateway_trade_republic",
        "home_assistant_app/portfolio_architect_gateway_import",
    }


def path_findings(relative: str) -> list[Finding]:
    normalized = normalize_member_path(relative)
    path = PurePosixPath(normalized)
    findings: list[Finding] = []
    if not normalized:
        return findings
    approved_privateish = normalized in ALLOWED_PRIVATEISH_PATHS
    folded_parts = {part.casefold() for part in path.parts}
    if not approved_privateish and folded_parts & FORBIDDEN_PATH_PARTS:
        findings.append(Finding("forbidden-private-path", relative))
    folded_name = path.name.casefold()
    if not approved_privateish and (
        folded_name in FORBIDDEN_BASENAMES or folded_name.startswith(".env")
    ):
        findings.append(Finding("forbidden-private-filename", relative))
    if normalized.startswith("tests/fixtures/") and normalized not in ALLOWED_CSV_PATHS:
        findings.append(Finding("unapproved-fixture", relative))
    suffix = path.suffix.casefold()
    if suffix in FORBIDDEN_SUFFIXES:
        findings.append(Finding("forbidden-private-filetype", relative))
    if suffix == ".png" and not is_allowed_png(normalized):
        findings.append(Finding("unexpected-image", relative))
    if suffix == ".csv" and normalized not in ALLOWED_CSV_PATHS:
        findings.append(Finding("unapproved-csv", relative))
    return findings


def iban_is_valid(candidate: str) -> bool:
    value = "".join(candidate.split()).upper()
    if not (15 <= len(value) <= 34):
        return False
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]+", value):
        return False
    rearranged = value[4:] + value[:4]
    remainder = 0
    for char in rearranged:
        digits = char if char.isdigit() else str(ord(char) - ord("A") + 10)
        for digit in digits:
            remainder = (remainder * 10 + int(digit)) % 97
    return remainder == 1


def is_synthetic_identity(value: str) -> bool:
    candidate = value.strip()
    if any(regex.fullmatch(candidate) for regex in SYNTHETIC_VALUE_RES):
        return True
    # Repeated-digit depot placeholders such as 111111111 / 222222222.
    if len(candidate) >= 6 and candidate.isdigit() and len(set(candidate)) == 1:
        return True
    return False


def text_findings(text: str, location: str, private_literals: tuple[str, ...]) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    for number, line in enumerate(lines, 1):
        if PRIVATE_KEY_RE.search(line):
            findings.append(Finding("private-key-material", location, number))
        for match in IBAN_CANDIDATE_RE.finditer(line.upper()):
            if iban_is_valid(match.group(1)):
                findings.append(Finding("valid-iban", location, number))
        for match in IDENTITY_FIELD_RE.finditer(line):
            value = match.group(2).strip()
            # URL/query/code expressions are not literal provider identities.
            if any(token in value for token in ("{", "}", "(", ")", "[", "]")):
                continue
            if not is_synthetic_identity(value):
                findings.append(Finding("provider-identity-literal", location, number))
        for match in ATTRIBUTION_FIELD_RE.finditer(line):
            value = match.group(2).strip()
            if any(token in value for token in ("{", "}", "(", ")", "[", "]")):
                continue
            if not is_synthetic_identity(value):
                findings.append(Finding("provider-attribution-literal", location, number))
    for index, literal in enumerate(private_literals, 1):
        if literal and literal in text:
            # Never print the literal itself.
            line = text.count("\n", 0, text.index(literal)) + 1
            findings.append(Finding(f"known-private-literal-{index}", location, line))
    return findings


def decode_text(data: bytes) -> str | None:
    if len(data) > MAX_TEXT_BYTES or b"\x00" in data[:4096]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def source_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.suffix.casefold() in EXCLUDED_SUFFIXES:
            continue
        yield path


def load_private_literals(root: Path, path: Path | None) -> tuple[str, ...]:
    if path is None:
        environment = os.environ.get("PORTFOLIO_ARCHITECT_PRIVATE_LITERALS_FILE", "").strip()
        path = Path(environment) if environment else None
    if path is None:
        return ()
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        pass
    else:
        raise SystemExit("Private-literals file must remain outside the repository")
    values = []
    for raw in resolved.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        if len(value) < 4:
            raise SystemExit("Private literals must contain at least four characters")
        values.append(value)
    return tuple(values)


def scan_source(root: Path, private_literals: tuple[str, ...]) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(root.rglob("*")):
        relative_path = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative_path.parts):
            continue
        if path.is_symlink():
            findings.append(Finding("forbidden-symlink", relative_path.as_posix()))
    for path in source_files(root):
        relative = path.relative_to(root).as_posix()
        findings.extend(path_findings(relative))
        data = path.read_bytes()
        text = decode_text(data)
        if text is not None:
            findings.extend(text_findings(text, relative, private_literals))
    return findings


def _git_bytes(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        # Do not echo Git stderr: a path/filter warning could itself contain
        # private material. The publication gate only needs a fail-closed result.
        raise SystemExit("Git history privacy scan failed")
    return result.stdout


def scan_history(root: Path, private_literals: tuple[str, ...]) -> list[Finding]:
    """Scan all reachable Git paths and textual patch history for private material."""
    count_raw = _git_bytes(root, "rev-list", "--all", "--count").strip()
    try:
        count = int(count_raw)
    except ValueError as err:
        raise SystemExit("Cannot determine reachable Git history") from err
    if count <= 0:
        raise SystemExit("Refusing privacy history scan: Git history is empty")

    findings: list[Finding] = []
    names = _git_bytes(root, "log", "--all", "--format=", "--name-only", "-z", "--", ".")
    for raw in names.split(b"\0"):
        name = raw.decode("utf-8", errors="replace").strip("\r\n")
        if name:
            findings.extend(path_findings(name))

    patch = _git_bytes(root, "log", "-p", "--all", "--no-ext-diff", "--text", "--", ".")
    text = patch.decode("utf-8", errors="replace")
    findings.extend(text_findings(text, "git-history", private_literals))
    return findings


def safe_zip_members(path: Path) -> Iterator[tuple[zipfile.ZipInfo, bytes]]:
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
            yield info, archive.read(info)


def scan_dist(dist: Path, private_literals: tuple[str, ...]) -> list[Finding]:
    findings: list[Finding] = []
    if not dist.is_dir():
        raise SystemExit(f"Release directory does not exist: {dist}")
    for path in sorted(dist.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.casefold() == ".zip":
            for info, data in safe_zip_members(path):
                location = f"{path.name}!/{info.filename}"
                findings.extend(path_findings(info.filename))
                text = decode_text(data)
                if text is not None:
                    findings.extend(text_findings(text, location, private_literals))
            continue
        # Convenience release files are expected to be text/JSON/YAML. The ZIP
        # filenames themselves are release transport, not nested source content.
        if path.suffix.casefold() != ".zip":
            findings.extend(path_findings(path.name))
        text = decode_text(path.read_bytes())
        if text is not None:
            findings.extend(text_findings(text, path.name, private_literals))
    return findings


def stage_dist(dist: Path, destination: Path) -> None:
    """Safely stage release contents for an independent Gitleaks directory scan."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for path in sorted(dist.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.casefold() != ".zip":
            shutil.copy2(path, destination / path.name)
            continue
        archive_root = destination / path.stem
        archive_root.mkdir()
        for info, data in safe_zip_members(path):
            target = archive_root.joinpath(*PurePosixPath(info.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)


def fail_on_findings(findings: Iterable[Finding]) -> None:
    unique = sorted({finding.render() for finding in findings})
    if not unique:
        return
    print("Portfolio Architect privacy publication gate FAILED:")
    for item in unique:
        print(f"- {item}")
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dist", type=Path)
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--stage-dist-for-gitleaks", type=Path)
    parser.add_argument("--private-literals", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    private_literals = load_private_literals(root, args.private_literals)
    findings = scan_source(root, private_literals)
    if args.history:
        findings.extend(scan_history(root, private_literals))
    if args.dist is not None:
        findings.extend(scan_dist(args.dist.resolve(), private_literals))
    fail_on_findings(findings)
    if args.stage_dist_for_gitleaks is not None:
        if args.dist is None:
            raise SystemExit("--stage-dist-for-gitleaks requires --dist")
        stage_dist(args.dist.resolve(), args.stage_dist_for_gitleaks.resolve())
    scopes = ["repository"]
    if args.history:
        scopes.append("complete Git history")
    if args.dist is not None:
        scopes.append("release artifacts")
    print(f"Validated Portfolio Architect privacy hygiene for {', '.join(scopes)}")


if __name__ == "__main__":
    main()
