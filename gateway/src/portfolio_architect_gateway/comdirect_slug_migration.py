"""Explicit one-time migration from the historical Comdirect App slug.

The migration deliberately preserves long-lived provider state, the Gateway bearer
secret, and the private-CA trust anchor while *not* copying the Comdirect OAuth
session.  The legacy App is frozen before export and the provider-qualified App
must establish a fresh PhotoTAN session before it publishes Supervisor discovery.
"""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import http.client
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import re
import secrets
import shutil
import ssl
import subprocess
import tempfile
import threading
from typing import Any, Final

from .models import parse_snapshot_bytes, validate_snapshot
from .runtime_config import normalise_secret
from .supervisor_tls import _certificate_sha256, _read_ca_certificate, _validate_tls_directory

_LOGGER = logging.getLogger(__name__)

MIGRATION_SCHEMA_VERSION: Final = 1
MIGRATION_RECEIVER_PORT: Final = 8788
MAX_MIGRATION_BODY_BYTES: Final = 4 * 1024 * 1024
MAX_MIGRATION_FILE_BYTES: Final = 2 * 1024 * 1024
MAX_MIGRATION_FILES: Final = 24
MIGRATION_CODE_RE: Final = re.compile(r"^([0-9a-f]{64})\.([A-Za-z0-9_-]{43,128})$")
HOST_SUFFIX_LEGACY: Final = "-portfolio-architect-gateway"
HOST_SUFFIX_COMDIRECT: Final = "-portfolio-architect-gateway-comdirect"
EXPORT_MARKER_NAME: Final = "comdirect-slug-migration-export.json"
IMPORT_MARKER_NAME: Final = "comdirect-slug-migration-import.json"
FREEZE_MARKER_NAME: Final = "comdirect-slug-migration-frozen.json"
CUTOVER_MARKER_NAME: Final = "comdirect-slug-migration-cutover-approved.json"
FRESH_SETUP_MARKER_NAME: Final = "comdirect-slug-fresh-setup.json"
STAGING_DIRECTORY_NAME: Final = "comdirect-slug-migration-staging"
TRANSPORT_DIRECTORY_NAME: Final = "comdirect-slug-migration-transport"

# OAuth/session state is intentionally excluded.  The new App performs a fresh
# provider authentication before discovery/cut-over.
_REQUIRED_MIGRATION_FILES: Final = frozenset(
    {
        "gateway-api-token",
        "portfolio.json",
        "tls/ca-key.pem",
        "tls/ca-cert.pem",
        "tls/server-key.pem",
        "tls/server-cert.pem",
        "tls/hostname",
    }
)
_OPTIONAL_MIGRATION_FILES: Final = frozenset(
    {
        "comdirect-client-id",
        "comdirect-client-secret",
        "investment-account.json",
        "investment-cash-policy.json",
        "comdirect-acquisition.json",
        "comdirect-csv-holdings.json",
        "comdirect-csv-cash.json",
    }
)
_ALLOWED_MIGRATION_FILES: Final = _REQUIRED_MIGRATION_FILES | _OPTIONAL_MIGRATION_FILES
_FORBIDDEN_MIGRATION_FILES: Final = frozenset(
    {
        "comdirect-session.json",
        "comdirect-acquisition-pending.json",
        EXPORT_MARKER_NAME,
        IMPORT_MARKER_NAME,
        FREEZE_MARKER_NAME,
        CUTOVER_MARKER_NAME,
        FRESH_SETUP_MARKER_NAME,
    }
)


@dataclass(frozen=True, slots=True)
class MigrationSummary:
    """Privacy-bounded staged migration metadata."""

    source_hostname: str
    source_ca_sha256: str
    snapshot_generated_at: str
    snapshot_sha256: str
    acquisition_mode: str
    file_count: int
    payload_sha256: str


@dataclass(frozen=True, slots=True)
class MigrationTransport:
    """One ephemeral pinned-TLS receiver identity."""

    hostname: str
    cert_file: Path
    key_file: Path
    cert_sha256: str
    token: str

    @property
    def code(self) -> str:
        return f"{self.cert_sha256}.{self.token}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def expected_successor_hostname(legacy_hostname: str) -> str:
    """Return only the provider-qualified successor of one historical hostname."""
    hostname = _normalise_hostname(legacy_hostname)
    if not hostname.endswith(HOST_SUFFIX_LEGACY) or hostname.endswith(HOST_SUFFIX_COMDIRECT):
        raise ValueError("Legacy Comdirect App hostname is not recognized")
    prefix = hostname[: -len(HOST_SUFFIX_LEGACY)]
    if not prefix or len(prefix) > 128:
        raise ValueError("Legacy Comdirect App hostname prefix is invalid")
    return f"{prefix}{HOST_SUFFIX_COMDIRECT}"


def expected_legacy_hostname(successor_hostname: str) -> str:
    """Return only the historical predecessor of one provider-qualified hostname."""
    hostname = _normalise_hostname(successor_hostname)
    if not hostname.endswith(HOST_SUFFIX_COMDIRECT):
        raise ValueError("Provider-qualified Comdirect App hostname is not recognized")
    prefix = hostname[: -len(HOST_SUFFIX_COMDIRECT)]
    if not prefix or len(prefix) > 128:
        raise ValueError("Provider-qualified Comdirect App hostname prefix is invalid")
    return f"{prefix}{HOST_SUFFIX_LEGACY}"


def _normalise_hostname(value: str) -> str:
    hostname = value.strip().lower().rstrip(".")
    if (
        not 1 <= len(hostname) <= 253
        or re.fullmatch(
            r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*",
            hostname,
        )
        is None
    ):
        raise ValueError("Migration hostname is invalid")
    return hostname


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_export_payload(
    data_directory: Path,
    *,
    options: dict[str, Any],
    source_hostname: str,
) -> tuple[dict[str, Any], MigrationSummary]:
    """Build one bounded in-memory export from the legacy App-private state."""
    data_directory = Path(data_directory)
    source_hostname = _normalise_hostname(source_hostname)
    expected_successor_hostname(source_hostname)
    if (data_directory / "comdirect-acquisition-pending.json").exists():
        raise ValueError("A Comdirect acquisition switch is still pending")
    for child in data_directory.rglob("*"):
        if child.is_symlink():
            raise ValueError("Symlinks are not permitted in migration state")

    validated_options = _validate_options(options)
    files: dict[str, dict[str, str | int]] = {}
    total = 0
    for relative in sorted(_ALLOWED_MIGRATION_FILES):
        path = data_directory / relative
        if not path.exists():
            continue
        if not path.is_file() or path.is_symlink():
            raise ValueError("Migration state contains an invalid file")
        body = path.read_bytes()
        if not body or len(body) > MAX_MIGRATION_FILE_BYTES:
            raise ValueError("Migration state file is empty or too large")
        total += len(body)
        if total > MAX_MIGRATION_BODY_BYTES // 2:
            raise ValueError("Migration state exceeds the supported size")
        files[relative] = {
            "size": len(body),
            "sha256": _sha256_bytes(body),
            "data": base64.b64encode(body).decode("ascii"),
        }
    missing = _REQUIRED_MIGRATION_FILES - set(files)
    if missing:
        raise ValueError("Legacy Comdirect state is incomplete for migration")
    if any((data_directory / name).exists() for name in _FORBIDDEN_MIGRATION_FILES - {EXPORT_MARKER_NAME}):
        # comdirect-session.json is expected to exist on live installs and is
        # intentionally not exported.  Only a pending acquisition marker blocks.
        if (data_directory / "comdirect-acquisition-pending.json").exists():
            raise ValueError("A Comdirect acquisition switch is still pending")

    payload: dict[str, Any] = {
        "schema_version": MIGRATION_SCHEMA_VERSION,
        "source_hostname": source_hostname,
        "oauth_session_transferred": False,
        "options": validated_options,
        "files": files,
    }
    body = _canonical_json_bytes(payload)
    if len(body) > MAX_MIGRATION_BODY_BYTES:
        raise ValueError("Migration payload exceeds the supported size")
    summary = _validate_payload(payload, expected_source_hostname=source_hostname)
    return payload, summary


def _validate_options(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {
        "poll_interval_seconds",
        "max_cached_snapshot_age_seconds",
        "request_timeout_seconds",
        "mfa_timeout_seconds",
        "health_endpoint_enabled",
        "depot_ids",
    }:
        raise ValueError("Comdirect App options are invalid for migration")
    result: dict[str, Any] = {}
    bounds = {
        "poll_interval_seconds": (300, 86400),
        "max_cached_snapshot_age_seconds": (0, 2592000),
        "request_timeout_seconds": (5, 60),
        "mfa_timeout_seconds": (30, 600),
    }
    for key, (minimum, maximum) in bounds.items():
        value = raw[key]
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise ValueError("Comdirect App options are invalid for migration")
        result[key] = value
    if not isinstance(raw["health_endpoint_enabled"], bool):
        raise ValueError("Comdirect App options are invalid for migration")
    result["health_endpoint_enabled"] = raw["health_endpoint_enabled"]
    depot_ids = raw["depot_ids"]
    if not isinstance(depot_ids, list) or len(depot_ids) > 32:
        raise ValueError("Comdirect depot filter is invalid for migration")
    cleaned: list[str] = []
    for item in depot_ids:
        if (
            not isinstance(item, str)
            or not 1 <= len(item) <= 64
            or item != item.strip()
            or any(ord(ch) < 33 or ord(ch) > 126 for ch in item)
            or item in cleaned
        ):
            raise ValueError("Comdirect depot filter is invalid for migration")
        cleaned.append(item)
    result["depot_ids"] = cleaned
    return result


def _validate_payload(
    raw: dict[str, Any],
    *,
    expected_source_hostname: str,
) -> MigrationSummary:
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version",
        "source_hostname",
        "oauth_session_transferred",
        "options",
        "files",
    }:
        raise ValueError("Migration payload structure is invalid")
    if raw["schema_version"] != MIGRATION_SCHEMA_VERSION or raw["oauth_session_transferred"] is not False:
        raise ValueError("Migration payload schema is unsupported")
    source_hostname = _normalise_hostname(str(raw["source_hostname"]))
    if source_hostname != _normalise_hostname(expected_source_hostname):
        raise ValueError("Migration payload source hostname does not match")
    expected_successor_hostname(source_hostname)
    _validate_options(raw["options"])
    files = raw["files"]
    if not isinstance(files, dict) or not _REQUIRED_MIGRATION_FILES.issubset(files) or len(files) > MAX_MIGRATION_FILES:
        raise ValueError("Migration file inventory is invalid")
    if set(files) - _ALLOWED_MIGRATION_FILES:
        raise ValueError("Migration payload contains an unexpected file")
    decoded: dict[str, bytes] = {}
    total = 0
    for relative, record in files.items():
        if not isinstance(relative, str) or relative not in _ALLOWED_MIGRATION_FILES:
            raise ValueError("Migration file name is invalid")
        if not isinstance(record, dict) or set(record) != {"size", "sha256", "data"}:
            raise ValueError("Migration file metadata is invalid")
        size = record["size"]
        digest = record["sha256"]
        data = record["data"]
        if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= MAX_MIGRATION_FILE_BYTES:
            raise ValueError("Migration file size is invalid")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("Migration file digest is invalid")
        if not isinstance(data, str) or len(data) > MAX_MIGRATION_FILE_BYTES * 2:
            raise ValueError("Migration file encoding is invalid")
        try:
            body = base64.b64decode(data, validate=True)
        except (ValueError, TypeError) as err:
            raise ValueError("Migration file encoding is invalid") from err
        if len(body) != size or _sha256_bytes(body) != digest:
            raise ValueError("Migration file integrity check failed")
        total += len(body)
        if total > MAX_MIGRATION_BODY_BYTES // 2:
            raise ValueError("Migration state exceeds the supported size")
        decoded[relative] = body

    # Validate the long-term bearer token without disclosing it.
    normalise_secret(
        decoded["gateway-api-token"].decode("ascii").strip(),
        name="gateway API token",
        minimum=32,
        maximum=512,
    )

    snapshot = validate_snapshot(parse_snapshot_bytes(decoded["portfolio.json"]))
    snapshot_body = snapshot.to_bytes()
    # The stored snapshot is canonical by contract; reject a non-canonical import.
    if snapshot_body != decoded["portfolio.json"]:
        raise ValueError("Migrated portfolio snapshot is not canonical")

    try:
        ca_pem = decoded["tls/ca-cert.pem"].decode("ascii")
    except UnicodeDecodeError as err:
        raise ValueError("Migrated CA certificate is invalid") from err
    ca_sha256 = _certificate_sha256(ca_pem)

    acquisition_mode = "live_api"
    acquisition_record = decoded.get("comdirect-acquisition.json")
    if acquisition_record is not None:
        state = json.loads(acquisition_record.decode("utf-8"))
        if not isinstance(state, dict) or state.get("schema_version") != 1:
            raise ValueError("Migrated acquisition state is invalid")
        mode = state.get("mode")
        if mode not in {"live_api", "csv"}:
            raise ValueError("Migrated acquisition mode is invalid")
        acquisition_mode = str(mode)

    return MigrationSummary(
        source_hostname=source_hostname,
        source_ca_sha256=ca_sha256,
        snapshot_generated_at=snapshot.generated_at.astimezone(timezone.utc).isoformat(timespec="seconds"),
        snapshot_sha256=_sha256_bytes(decoded["portfolio.json"]),
        acquisition_mode=acquisition_mode,
        file_count=len(decoded),
        payload_sha256=_sha256_bytes(_canonical_json_bytes(raw)),
    )


def stage_payload(
    raw: dict[str, Any],
    *,
    staging_directory: Path,
    expected_source_hostname: str,
) -> MigrationSummary:
    """Validate and persist one staged migration into isolated private state."""
    summary = _validate_payload(raw, expected_source_hostname=expected_source_hostname)
    staging_directory = Path(staging_directory)
    parent = staging_directory.parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".comdirect-migration-", dir=parent) as temp_name:
        temporary = Path(temp_name)
        os.chmod(temporary, 0o700)
        files = raw["files"]
        assert isinstance(files, dict)
        for relative, record in files.items():
            assert isinstance(relative, str) and isinstance(record, dict)
            body = base64.b64decode(str(record["data"]), validate=True)
            target = temporary / relative
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(body)
            os.chmod(target, 0o600)
        (temporary / "migration-options.json").write_text(
            json.dumps(raw["options"], sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary / "migration-options.json", 0o600)
        (temporary / "migration-summary.json").write_text(
            json.dumps(asdict(summary), sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary / "migration-summary.json", 0o600)
        # Validate the imported TLS directory before making the staged tree visible.
        _validate_tls_directory(temporary / "tls")
        if staging_directory.exists():
            shutil.rmtree(staging_directory)
        os.replace(temporary, staging_directory)
    return summary


def read_staged_summary(staging_directory: Path) -> MigrationSummary | None:
    path = Path(staging_directory) / "migration-summary.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return MigrationSummary(**raw)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def commit_staged_payload(
    *,
    staging_directory: Path,
    data_directory: Path,
    import_marker: Path,
) -> tuple[MigrationSummary, dict[str, Any]]:
    """Crash-safely install staged long-lived state without any OAuth session.

    The provider-qualified App remains in a non-discoverable setup shell throughout
    this operation. A private commit marker is written before any target files; if
    the process stops mid-copy, the next explicit commit discards that incomplete
    target tree and replays the already-validated staging set. The completed import
    marker is written last and is the only condition that permits later cut-over.
    """
    staging_directory = Path(staging_directory)
    data_directory = Path(data_directory)
    import_marker = Path(import_marker)
    summary = read_staged_summary(staging_directory)
    if summary is None:
        raise ValueError("No validated Comdirect migration is staged")
    options_path = staging_directory / "migration-options.json"
    options = _validate_options(json.loads(options_path.read_text(encoding="utf-8")))
    required = {staging_directory / item for item in _REQUIRED_MIGRATION_FILES}
    if any(not item.is_file() or item.is_symlink() for item in required):
        raise ValueError("Staged Comdirect migration is incomplete")

    data_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    commit_marker = data_directory / ".comdirect-slug-migration-committing.json"

    # Completed import is idempotent only when its exact privacy-bounded identity
    # matches the staging set.
    if import_marker.is_file():
        try:
            marker = json.loads(import_marker.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            marker = None
        if (
            isinstance(marker, dict)
            and marker.get("schema_version") == 1
            and marker.get("source_ca_sha256") == summary.source_ca_sha256
            and marker.get("source_snapshot_sha256") == summary.snapshot_sha256
            and marker.get("source_hostname") == summary.source_hostname
            and marker.get("oauth_session_transferred") is False
        ):
            return summary, options
        raise ValueError("Provider-qualified Comdirect App already contains different private state")

    # A prior interrupted commit is safe to discard because this App has not been
    # allowed to enter canonical runtime or publish discovery yet.
    if commit_marker.exists():
        for child in tuple(data_directory.iterdir()):
            if child.is_symlink():
                raise ValueError("Provider-qualified Comdirect target state contains a symlink")
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    unexpected = [item for item in data_directory.iterdir() if item.name != commit_marker.name]
    if unexpected:
        raise ValueError("Provider-qualified Comdirect App already contains private state")

    _atomic_private_json(
        commit_marker,
        {
            "schema_version": 1,
            "source_hostname": summary.source_hostname,
            "payload_sha256": summary.payload_sha256,
            "started_at": _utc_now(),
        },
    )
    try:
        for relative in sorted(_ALLOWED_MIGRATION_FILES):
            source = staging_directory / relative
            if not source.is_file():
                continue
            target = data_directory / relative
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.migration-{secrets.token_hex(8)}")
            temporary.write_bytes(source.read_bytes())
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
        (data_directory / "comdirect-session.json").unlink(missing_ok=True)
        (data_directory / "comdirect-acquisition-pending.json").unlink(missing_ok=True)
        _validate_tls_directory(data_directory / "tls")
        snapshot_bytes = (data_directory / "portfolio.json").read_bytes()
        snapshot = validate_snapshot(parse_snapshot_bytes(snapshot_bytes))
        if snapshot.to_bytes() != snapshot_bytes:
            raise ValueError("Prepared portfolio snapshot is not canonical")
        marker = {
            "schema_version": 1,
            "source_hostname": summary.source_hostname,
            "source_ca_sha256": summary.source_ca_sha256,
            "source_snapshot_sha256": summary.snapshot_sha256,
            "source_snapshot_generated_at": summary.snapshot_generated_at,
            "source_acquisition_mode": summary.acquisition_mode,
            "oauth_session_transferred": False,
            "options_applied": False,
            "imported_at": _utc_now(),
        }
        _atomic_private_json(import_marker, marker)
        commit_marker.unlink()
    except Exception:
        # Leave the commit marker in place; no discovery/canonical runtime can start,
        # and the next commit will discard and replay the incomplete target state.
        raise
    return summary, options

def mark_import_options_applied(import_marker: Path) -> None:
    """Mark migrated Supervisor options complete without changing migration identity."""
    path = Path(import_marker)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as err:
        raise ValueError("Comdirect import marker is invalid") from err
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("Comdirect import marker is invalid")
    document["options_applied"] = True
    document["options_applied_at"] = _utc_now()
    _atomic_private_json(path, document)


def import_options_applied(import_marker: Path) -> bool:
    try:
        document = json.loads(Path(import_marker).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return bool(
        isinstance(document, dict)
        and document.get("schema_version") == 1
        and document.get("options_applied") is True
        and document.get("oauth_session_transferred") is False
    )

def _atomic_private_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}")
    temporary.write_text(
        json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def prepare_migration_transport(
    base_directory: Path,
    hostname: str,
) -> MigrationTransport:
    """Create one ephemeral self-signed receiver certificate and one-time token."""
    hostname = _normalise_hostname(hostname)
    expected_legacy_hostname(hostname)
    directory = Path(base_directory) / TRANSPORT_DIRECTORY_NAME
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(mode=0o700, parents=True)
    key = directory / "migration-key.pem"
    cert = directory / "migration-cert.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-sha256",
            "-nodes",
            "-days",
            "2",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-subj",
            f"/CN={hostname}",
            "-addext",
            f"subjectAltName=DNS:{hostname}",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
    )
    os.chmod(key, 0o600)
    os.chmod(cert, 0o600)
    pem = cert.read_text(encoding="ascii")
    der = ssl.PEM_cert_to_DER_cert(pem)
    fingerprint = _sha256_bytes(der)
    return MigrationTransport(
        hostname=hostname,
        cert_file=cert,
        key_file=key,
        cert_sha256=fingerprint,
        token=secrets.token_urlsafe(48),
    )


def parse_migration_code(value: str) -> tuple[str, str]:
    cleaned = value.strip()
    match = MIGRATION_CODE_RE.fullmatch(cleaned)
    if match is None:
        raise ValueError("Migration code is invalid")
    return match.group(1), match.group(2)


def send_payload_to_successor(
    *,
    legacy_hostname: str,
    migration_code: str,
    payload: dict[str, Any],
    timeout_seconds: int = 20,
) -> MigrationSummary:
    """Send state only to the exact provider-qualified successor using leaf pinning."""
    cert_sha256, token = parse_migration_code(migration_code)
    target = expected_successor_hostname(legacy_hostname)
    body = _canonical_json_bytes(payload)
    if not 1 <= len(body) <= MAX_MIGRATION_BODY_BYTES:
        raise ValueError("Migration payload size is invalid")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    connection = http.client.HTTPSConnection(
        target,
        MIGRATION_RECEIVER_PORT,
        context=context,
        timeout=timeout_seconds,
    )
    try:
        connection.connect()
        peer = connection.sock.getpeercert(binary_form=True) if connection.sock else None
        if not peer or not secrets.compare_digest(_sha256_bytes(peer), cert_sha256):
            raise ValueError("Provider-qualified migration receiver certificate did not match")
        connection.request(
            "POST",
            "/migration/v1/stage",
            body=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        response_body = response.read(16 * 1024)
        if response.status != HTTPStatus.OK:
            raise ValueError("Provider-qualified migration receiver rejected the transfer")
        document = json.loads(response_body.decode("utf-8"))
        if not isinstance(document, dict) or document.get("status") != "staged":
            raise ValueError("Provider-qualified migration receiver returned invalid status")
        summary = MigrationSummary(**document["summary"])
        expected = _validate_payload(payload, expected_source_hostname=legacy_hostname)
        if summary != expected:
            raise ValueError("Provider-qualified migration receiver staged unexpected state")
        return summary
    finally:
        connection.close()


def successor_status(
    *,
    legacy_hostname: str,
    migration_code: str,
    timeout_seconds: int = 10,
) -> tuple[str, MigrationSummary | None]:
    """Return the pinned successor receiver status without sending state."""
    cert_sha256, token = parse_migration_code(migration_code)
    target = expected_successor_hostname(legacy_hostname)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    connection = http.client.HTTPSConnection(
        target, MIGRATION_RECEIVER_PORT, context=context, timeout=timeout_seconds
    )
    try:
        connection.connect()
        peer = connection.sock.getpeercert(binary_form=True) if connection.sock else None
        if not peer or not secrets.compare_digest(_sha256_bytes(peer), cert_sha256):
            raise ValueError("Provider-qualified migration receiver certificate did not match")
        connection.request(
            "GET",
            "/migration/v1/status",
            headers={"Authorization": f"Bearer {token}", "Connection": "close"},
        )
        response = connection.getresponse()
        body = response.read(16 * 1024)
        if response.status != HTTPStatus.OK:
            raise ValueError("Provider-qualified migration receiver status failed")
        document = json.loads(body.decode("utf-8"))
        if not isinstance(document, dict) or document.get("status") not in {
            "waiting", "staged", "committed"
        }:
            raise ValueError("Provider-qualified migration receiver returned invalid status")
        raw_summary = document.get("summary")
        summary = MigrationSummary(**raw_summary) if isinstance(raw_summary, dict) else None
        return str(document["status"]), summary
    finally:
        connection.close()


def write_export_marker(path: Path, summary: MigrationSummary) -> None:
    """Persist only privacy-bounded evidence that the successor staged the export."""
    document = asdict(summary)
    document.update({"schema_version": 1, "staged_at": _utc_now()})
    _atomic_private_json(Path(path), document)


def read_export_marker(path: Path) -> MigrationSummary | None:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        return None
    try:
        return MigrationSummary(
            source_hostname=document["source_hostname"],
            source_ca_sha256=document["source_ca_sha256"],
            snapshot_generated_at=document["snapshot_generated_at"],
            snapshot_sha256=document["snapshot_sha256"],
            acquisition_mode=document["acquisition_mode"],
            file_count=document["file_count"],
            payload_sha256=document["payload_sha256"],
        )
    except (KeyError, TypeError, ValueError):
        return None


def write_freeze_marker(path: Path, *, successor_hostname: str) -> None:
    """Persist an explicit legacy freeze before stopping provider activity."""
    successor = _normalise_hostname(successor_hostname)
    expected_legacy_hostname(successor)
    _atomic_private_json(
        Path(path),
        {
            "schema_version": 1,
            "successor_hostname": successor,
            "frozen_at": _utc_now(),
            "provider_calls_disabled": True,
        },
    )


def legacy_is_frozen(path: Path) -> bool:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return bool(
        isinstance(document, dict)
        and document.get("schema_version") == 1
        and document.get("provider_calls_disabled") is True
        and isinstance(document.get("successor_hostname"), str)
    )


def approve_cutover(path: Path, *, source_hostname: str, ca_sha256: str) -> None:
    """Persist the user's explicit approval to start the canonical App runtime."""
    source = _normalise_hostname(source_hostname)
    expected_successor_hostname(source)
    if re.fullmatch(r"[0-9a-f]{64}", ca_sha256) is None:
        raise ValueError("Comdirect migration CA fingerprint is invalid")
    _atomic_private_json(
        Path(path),
        {
            "schema_version": 1,
            "source_hostname": source,
            "source_ca_sha256": ca_sha256,
            "approved_at": _utc_now(),
        },
    )



def read_import_marker(path: Path) -> dict[str, Any] | None:
    """Return one validated privacy-bounded import marker."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        return None
    source = document.get("source_hostname")
    ca_sha256 = document.get("source_ca_sha256")
    snapshot_sha256 = document.get("source_snapshot_sha256")
    if (
        not isinstance(source, str)
        or re.fullmatch(r"[0-9a-f]{64}", str(ca_sha256)) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(snapshot_sha256)) is None
        or document.get("oauth_session_transferred") is not False
    ):
        return None
    try:
        expected_successor_hostname(source)
    except ValueError:
        return None
    return document


def cutover_marker_document(path: Path) -> dict[str, Any] | None:
    """Return one validated migration/fresh-setup cut-over marker."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        return None
    if document.get("fresh_setup") is True:
        return {"schema_version": 1, "fresh_setup": True}
    source = document.get("source_hostname")
    ca_sha256 = document.get("source_ca_sha256")
    if not isinstance(source, str) or re.fullmatch(r"[0-9a-f]{64}", str(ca_sha256)) is None:
        return None
    try:
        expected_successor_hostname(source)
    except ValueError:
        return None
    return document


def validate_committed_migration_identity(
    data_directory: Path,
    *,
    successor_hostname: str,
) -> str | None:
    """Validate committed migration identity and return the preserved CA fingerprint.

    ``None`` denotes an explicitly approved fresh setup. A migrated installation must
    have matching import/cut-over markers, the exact predecessor/successor hostname
    relationship, and the same private CA that was staged from the historical App.
    """
    data_directory = Path(data_directory)
    cutover = cutover_marker_document(data_directory / CUTOVER_MARKER_NAME)
    if cutover is None:
        raise ValueError("Provider-qualified Comdirect cut-over is not approved")
    if cutover.get("fresh_setup") is True:
        if not (data_directory / FRESH_SETUP_MARKER_NAME).is_file():
            raise ValueError("Fresh Comdirect setup marker is unavailable")
        return None
    imported = read_import_marker(data_directory / IMPORT_MARKER_NAME)
    if imported is None or not import_options_applied(data_directory / IMPORT_MARKER_NAME):
        raise ValueError("Committed Comdirect migration is incomplete")
    source = str(imported["source_hostname"])
    if expected_successor_hostname(source) != _normalise_hostname(successor_hostname):
        raise ValueError("Committed Comdirect migration hostname does not match this App")
    if cutover.get("source_hostname") != source:
        raise ValueError("Comdirect cut-over source identity does not match imported state")
    ca_sha256 = str(imported["source_ca_sha256"])
    if cutover.get("source_ca_sha256") != ca_sha256:
        raise ValueError("Comdirect cut-over trust identity does not match imported state")
    if not secrets.compare_digest(source_ca_fingerprint(data_directory), ca_sha256):
        raise ValueError("Migrated Comdirect private CA fingerprint changed before cut-over")
    if (data_directory / "comdirect-session.json").exists():
        raise ValueError("Migrated Comdirect OAuth session must not be present before cut-over")
    return ca_sha256

def _supervisor_request_document(
    method: str,
    path: str,
    *,
    supervisor_token: str,
    payload: dict[str, Any] | None = None,
    supervisor_url: str = "http://supervisor",
) -> dict[str, Any]:
    """Call only the fixed Supervisor origin with bounded JSON."""
    if supervisor_url != "http://supervisor":
        raise RuntimeError("Unexpected Supervisor API origin")
    if (
        not supervisor_token
        or len(supervisor_token) > 4096
        or any(ord(ch) < 33 or ord(ch) > 126 for ch in supervisor_token)
    ):
        raise RuntimeError("Supervisor token is unavailable or invalid")
    from urllib.request import Request, build_opener, ProxyHandler
    from urllib.error import HTTPError, URLError

    body = _canonical_json_bytes(payload) if payload is not None else None
    headers = {
        "Authorization": f"Bearer {supervisor_token}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(supervisor_url + path, data=body, method=method, headers=headers)
    try:
        with build_opener(ProxyHandler({})).open(request, timeout=10) as response:
            raw = response.read(64 * 1024 + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as err:
        raise RuntimeError("Supervisor migration request failed") from err
    if len(raw) > 64 * 1024:
        raise RuntimeError("Supervisor migration response exceeded the size limit")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as err:
        raise RuntimeError("Supervisor returned invalid migration JSON") from err
    if not isinstance(document, dict) or document.get("result") != "ok":
        raise RuntimeError("Supervisor rejected the migration request")
    return document


def read_self_options(
    *,
    supervisor_token: str,
    supervisor_url: str = "http://supervisor",
) -> dict[str, Any]:
    """Read and validate this App's current non-secret Supervisor options."""
    document = _supervisor_request_document(
        "GET",
        "/addons/self/info",
        supervisor_token=supervisor_token,
        supervisor_url=supervisor_url,
    )
    data = document.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Supervisor self-info response is invalid")
    options = data.get("options")
    if not isinstance(options, dict):
        raise RuntimeError("Supervisor self-info omitted App options")
    return _validate_options(options)


def update_self_options(
    options: dict[str, Any],
    *,
    supervisor_token: str,
    supervisor_url: str = "http://supervisor",
) -> None:
    """Persist migrated non-secret options through the App's own Supervisor endpoint."""
    validated = _validate_options(options)
    _supervisor_request_document(
        "POST",
        "/addons/self/options",
        supervisor_token=supervisor_token,
        supervisor_url=supervisor_url,
        payload={"options": validated},
    )


def ensure_self_options(
    options: dict[str, Any],
    *,
    supervisor_token: str,
    supervisor_url: str = "http://supervisor",
) -> None:
    """Idempotently apply migrated options and verify Supervisor persisted them."""
    validated = _validate_options(options)
    try:
        current = read_self_options(
            supervisor_token=supervisor_token, supervisor_url=supervisor_url
        )
    except RuntimeError:
        current = None
    if current != validated:
        update_self_options(
            validated, supervisor_token=supervisor_token, supervisor_url=supervisor_url
        )
        current = read_self_options(
            supervisor_token=supervisor_token, supervisor_url=supervisor_url
        )
    if current != validated:
        raise RuntimeError("Supervisor did not persist migrated Comdirect options")



class MigrationReceiverServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        transport: MigrationTransport,
        staging_directory: Path,
        expected_source_hostname: str,
    ) -> None:
        self.transport = transport
        self.staging_directory = Path(staging_directory)
        self.expected_source_hostname = expected_source_hostname
        self._lock = threading.RLock()
        self._summary: MigrationSummary | None = read_staged_summary(self.staging_directory)
        self.committed = False
        super().__init__(address, MigrationReceiverHandler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(str(transport.cert_file), str(transport.key_file))
        self.socket = context.wrap_socket(self.socket, server_side=True)

    @property
    def summary(self) -> MigrationSummary | None:
        with self._lock:
            return self._summary

    def stage(self, document: dict[str, Any]) -> MigrationSummary:
        with self._lock:
            if self.committed:
                raise ValueError("Comdirect migration is already committed")
            summary = stage_payload(
                document,
                staging_directory=self.staging_directory,
                expected_source_hostname=self.expected_source_hostname,
            )
            self._summary = summary
            return summary


class MigrationReceiverHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "PortfolioArchitectComdirectMigration"
    sys_version = ""

    @property
    def migration_server(self) -> MigrationReceiverServer:
        return self.server  # type: ignore[return-value]

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorised():
            self._empty(HTTPStatus.FORBIDDEN)
            return
        if self.path != "/migration/v1/status":
            self._empty(HTTPStatus.NOT_FOUND)
            return
        summary = self.migration_server.summary
        self._json(
            {
                "status": "committed" if self.migration_server.committed else ("staged" if summary else "waiting"),
                "summary": asdict(summary) if summary else None,
            }
        )

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorised():
            self._empty(HTTPStatus.FORBIDDEN)
            return
        if self.path != "/migration/v1/stage":
            self._empty(HTTPStatus.NOT_FOUND)
            return
        if self.headers.get_content_type() != "application/json":
            self._empty(HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
            return
        length_text = self.headers.get("Content-Length")
        if not length_text or not length_text.isdecimal():
            self._empty(HTTPStatus.LENGTH_REQUIRED)
            return
        length = int(length_text)
        if not 1 <= length <= MAX_MIGRATION_BODY_BYTES:
            self._empty(HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        body = self.rfile.read(length)
        if len(body) != length:
            self._empty(HTTPStatus.BAD_REQUEST)
            return
        try:
            document = json.loads(body.decode("utf-8"))
            if not isinstance(document, dict):
                raise ValueError
            summary = self.migration_server.stage(document)
        except (UnicodeError, json.JSONDecodeError, ValueError, OSError):
            _LOGGER.warning("Comdirect slug-migration payload was rejected")
            self._empty(HTTPStatus.BAD_REQUEST)
            return
        self._json({"status": "staged", "summary": asdict(summary)})

    def do_PUT(self) -> None:  # noqa: N802
        self._empty(HTTPStatus.METHOD_NOT_ALLOWED)

    do_PATCH = do_PUT
    do_DELETE = do_PUT
    do_HEAD = do_PUT
    do_OPTIONS = do_PUT

    def _authorised(self) -> bool:
        token = self.headers.get("Authorization", "")
        expected = f"Bearer {self.migration_server.transport.token}"
        if len(token) > 512 or not secrets.compare_digest(token, expected):
            return False
        # The receiver is not host-mapped and the exact DNS target is fixed by the
        # sender. Reject obviously external source addresses as defense in depth.
        try:
            import ipaddress

            address = ipaddress.ip_address(self.client_address[0])
        except ValueError:
            return False
        return address.is_private or address.is_loopback

    def _json(self, document: dict[str, Any]) -> None:
        body = _canonical_json_bytes(document)
        self.send_response(HTTPStatus.OK)
        self._headers("application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _empty(self, status: HTTPStatus) -> None:
        self.send_response(status)
        self._headers("text/plain; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _headers(self, content_type: str) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")

    def log_message(self, format: str, *args: Any) -> None:
        _LOGGER.info("Comdirect migration receiver request completed")


def source_ca_fingerprint(data_directory: Path) -> str:
    ca = _read_ca_certificate(Path(data_directory) / "tls/ca-cert.pem")
    return _certificate_sha256(ca)
