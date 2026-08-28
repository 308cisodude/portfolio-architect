"""Private-PKI TLS bootstrap and Supervisor trust discovery for HA Gateway Apps."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import ssl
import subprocess
import tempfile
import threading
import time
from typing import Any, Final
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

DISCOVERY_SERVICE: Final = "portfolio_architect"
DISCOVERY_TRANSPORT_SCHEMA_VERSION: Final = 1
GATEWAY_PORT: Final = 8787
GATEWAY_PATH: Final = "/api/v1/portfolio"
MAX_SUPERVISOR_RESPONSE_BYTES: Final = 64 * 1024
MAX_CA_CERTIFICATE_BYTES: Final = 16 * 1024
LEAF_RENEWAL_WINDOW_SECONDS: Final = 30 * 24 * 60 * 60
_CA_DAYS: Final = 3650
_LEAF_DAYS: Final = 825
_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*$"
)
_PROVIDER_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")


@dataclass(frozen=True, slots=True)
class SupervisorTlsMaterial:
    """Verified private-PKI material for one Supervisor-managed Gateway App."""

    hostname: str
    cert_file: Path
    key_file: Path
    ca_certificate_pem: str
    ca_sha256: str


def supervisor_app_hostname(
    *,
    supervisor_url: str = "http://supervisor",
    supervisor_token: str | None = None,
) -> str:
    """Return the validated Supervisor-assigned hostname for this App only."""
    token = supervisor_token or os.environ.get("SUPERVISOR_TOKEN", "")
    if not token or len(token) > 4096 or any(ord(ch) < 33 or ord(ch) > 126 for ch in token):
        raise RuntimeError("Supervisor token is unavailable or invalid")
    info = _supervisor_json("GET", "/addons/self/info", token, supervisor_url)
    return _normalise_hostname(info.get("hostname"))


def prepare_supervisor_tls(
    data_directory: Path,
    provider_id: str,
    *,
    supervisor_url: str = "http://supervisor",
    supervisor_token: str | None = None,
) -> SupervisorTlsMaterial:
    """Create or reuse private PKI material bound to the Supervisor app hostname."""
    provider = _normalise_provider_id(provider_id)
    token = supervisor_token or os.environ.get("SUPERVISOR_TOKEN", "")
    if not token or len(token) > 4096 or any(ord(ch) < 33 or ord(ch) > 126 for ch in token):
        raise RuntimeError("Supervisor token is unavailable or invalid")

    hostname = supervisor_app_hostname(supervisor_url=supervisor_url, supervisor_token=token)

    data_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    tls_dir = data_directory / "tls"
    if tls_dir.is_symlink():
        raise RuntimeError("Gateway TLS directory must not be a symlink")

    if not tls_dir.exists():
        _create_initial_material(data_directory, tls_dir, provider, hostname)
    else:
        _validate_tls_directory(tls_dir)
        stored_hostname = _read_small_text(tls_dir / "hostname", 253)
        if stored_hostname != hostname:
            _renew_leaf(tls_dir, hostname)
        elif not _leaf_is_usable(tls_dir, hostname):
            _renew_leaf(tls_dir, hostname)

    if not _leaf_is_usable(tls_dir, hostname):
        raise RuntimeError("Gateway TLS certificate material failed validation")

    ca_pem = _read_ca_certificate(tls_dir / "ca-cert.pem")
    ca_sha256 = _certificate_sha256(ca_pem)
    return SupervisorTlsMaterial(
        hostname=hostname,
        cert_file=tls_dir / "server-cert.pem",
        key_file=tls_dir / "server-key.pem",
        ca_certificate_pem=ca_pem,
        ca_sha256=ca_sha256,
    )



def start_supervisor_tls_discovery_publisher(
    material: SupervisorTlsMaterial,
    provider_id: str,
) -> threading.Thread:
    """Publish discovery asynchronously, retrying boundedly while the App keeps serving HTTPS."""
    provider = _normalise_provider_id(provider_id)

    def _worker() -> None:
        delay = 2.0
        for _attempt in range(8):
            try:
                publish_supervisor_tls_discovery(material, provider)
                return
            except RuntimeError:
                time.sleep(delay)
                delay = min(delay * 2.0, 60.0)

    thread = threading.Thread(
        target=_worker,
        name="portfolio-tls-discovery",
        daemon=True,
    )
    thread.start()
    return thread

def publish_supervisor_tls_discovery(
    material: SupervisorTlsMaterial,
    provider_id: str,
    *,
    supervisor_url: str = "http://supervisor",
    supervisor_token: str | None = None,
) -> str:
    """Publish public trust material through Supervisor discovery after HTTPS is live."""
    provider = _normalise_provider_id(provider_id)
    token = supervisor_token or os.environ.get("SUPERVISOR_TOKEN", "")
    if not token:
        raise RuntimeError("Supervisor token is unavailable")
    result = _supervisor_json(
        "POST",
        "/discovery",
        token,
        supervisor_url,
        payload={
            "service": DISCOVERY_SERVICE,
            "config": {
                "transport_schema_version": DISCOVERY_TRANSPORT_SCHEMA_VERSION,
                "provider_id": provider,
                "host": material.hostname,
                "port": GATEWAY_PORT,
                "path": GATEWAY_PATH,
                "ca_certificate": material.ca_certificate_pem,
                "ca_sha256": material.ca_sha256,
            },
        },
    )
    uuid = result.get("uuid")
    if not isinstance(uuid, str) or re.fullmatch(r"[0-9a-f]{32}", uuid) is None:
        raise RuntimeError("Supervisor returned an invalid discovery identifier")
    return uuid


def _supervisor_json(
    method: str,
    path: str,
    token: str,
    base_url: str,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if base_url != "http://supervisor":
        raise RuntimeError("Unexpected Supervisor API origin")
    body = None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    opener = build_opener(ProxyHandler({}))
    request = Request(base_url + path, data=body, headers=headers, method=method)
    try:
        with opener.open(request, timeout=10) as response:
            raw = response.read(MAX_SUPERVISOR_RESPONSE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as err:
        raise RuntimeError("Supervisor API request failed") from err
    if len(raw) > MAX_SUPERVISOR_RESPONSE_BYTES:
        raise RuntimeError("Supervisor API response exceeded the size limit")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise RuntimeError("Supervisor API returned invalid JSON") from err
    if not isinstance(document, dict) or document.get("result") != "ok":
        raise RuntimeError("Supervisor API rejected the request")
    data = document.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Supervisor API response did not contain an object")
    return data


def _create_initial_material(
    data_directory: Path,
    tls_dir: Path,
    provider_id: str,
    hostname: str,
) -> None:
    temporary = Path(tempfile.mkdtemp(prefix=".tls-new-", dir=data_directory))
    try:
        os.chmod(temporary, 0o700)
        _run_openssl(
            "ecparam", "-name", "prime256v1", "-genkey", "-noout",
            "-out", str(temporary / "ca-key.pem"),
        )
        _run_openssl(
            "req", "-x509", "-new", "-sha256",
            "-key", str(temporary / "ca-key.pem"),
            "-out", str(temporary / "ca-cert.pem"),
            "-days", str(_CA_DAYS),
            "-subj", f"/CN=Portfolio Architect {provider_id} local CA",
            "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign",
            "-addext", "subjectKeyIdentifier=hash",
        )
        _generate_leaf_files(temporary, hostname)
        (temporary / "hostname").write_text(hostname, encoding="ascii")
        _secure_material_files(temporary)
        if not _leaf_is_usable(temporary, hostname):
            raise RuntimeError("Generated Gateway TLS certificate material is invalid")
        os.replace(temporary, tls_dir)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def _renew_leaf(tls_dir: Path, hostname: str) -> None:
    if not _ca_is_usable(tls_dir):
        raise RuntimeError("Existing Gateway CA is incomplete or invalid; refusing trust reset")
    temporary = Path(tempfile.mkdtemp(prefix=".leaf-new-", dir=tls_dir.parent))
    try:
        shutil.copy2(tls_dir / "ca-key.pem", temporary / "ca-key.pem")
        shutil.copy2(tls_dir / "ca-cert.pem", temporary / "ca-cert.pem")
        _generate_leaf_files(temporary, hostname)
        if not _leaf_is_usable(temporary, hostname):
            raise RuntimeError("Renewed Gateway TLS certificate failed validation")
        for name in ("server-key.pem", "server-cert.pem"):
            os.chmod(temporary / name, 0o600)
            os.replace(temporary / name, tls_dir / name)
        (tls_dir / "hostname").write_text(hostname, encoding="ascii")
        os.chmod(tls_dir / "hostname", 0o600)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def _generate_leaf_files(directory: Path, hostname: str) -> None:
    serial = secrets.token_hex(16)
    extension_file = directory / "server-ext.cnf"
    csr_file = directory / "server.csr"
    extension_file.write_text(
        "\n".join(
            (
                "basicConstraints=critical,CA:FALSE",
                "keyUsage=critical,digitalSignature",
                "extendedKeyUsage=serverAuth",
                f"subjectAltName=DNS:{hostname}",
                "subjectKeyIdentifier=hash",
                "authorityKeyIdentifier=keyid,issuer",
                "",
            )
        ),
        encoding="ascii",
    )
    try:
        _run_openssl(
            "ecparam", "-name", "prime256v1", "-genkey", "-noout",
            "-out", str(directory / "server-key.pem"),
        )
        _run_openssl(
            "req", "-new",
            "-key", str(directory / "server-key.pem"),
            "-out", str(csr_file),
            "-subj", f"/CN={hostname}",
        )
        _run_openssl(
            "x509", "-req", "-sha256",
            "-in", str(csr_file),
            "-CA", str(directory / "ca-cert.pem"),
            "-CAkey", str(directory / "ca-key.pem"),
            "-set_serial", f"0x{serial}",
            "-out", str(directory / "server-cert.pem"),
            "-days", str(_LEAF_DAYS),
            "-extfile", str(extension_file),
        )
    finally:
        csr_file.unlink(missing_ok=True)
        extension_file.unlink(missing_ok=True)


def _validate_tls_directory(tls_dir: Path) -> None:
    if not tls_dir.is_dir():
        raise RuntimeError("Gateway TLS path is not a directory")
    required = {"ca-key.pem", "ca-cert.pem", "server-key.pem", "server-cert.pem", "hostname"}
    for name in required:
        path = tls_dir / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("Gateway TLS material is incomplete; refusing trust reset")
        os.chmod(path, 0o600)
    os.chmod(tls_dir, 0o700)


def _ca_is_usable(directory: Path) -> bool:
    try:
        ca_pem = _read_ca_certificate(directory / "ca-cert.pem")
        _certificate_sha256(ca_pem)
        _run_openssl("pkey", "-in", str(directory / "ca-key.pem"), "-noout")
        _run_openssl("x509", "-in", str(directory / "ca-cert.pem"), "-noout", "-checkend", str(LEAF_RENEWAL_WINDOW_SECONDS))
    except (OSError, RuntimeError, ValueError, ssl.SSLError):
        return False
    return True


def _leaf_is_usable(directory: Path, hostname: str) -> bool:
    if not _ca_is_usable(directory):
        return False
    try:
        _run_openssl("verify", "-CAfile", str(directory / "ca-cert.pem"), str(directory / "server-cert.pem"))
        _run_openssl("x509", "-in", str(directory / "server-cert.pem"), "-noout", "-checkhost", hostname)
        _run_openssl("x509", "-in", str(directory / "server-cert.pem"), "-noout", "-checkend", str(LEAF_RENEWAL_WINDOW_SECONDS))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(directory / "server-cert.pem", directory / "server-key.pem")
    except (OSError, RuntimeError, ValueError, ssl.SSLError):
        return False
    return True


def _secure_material_files(directory: Path) -> None:
    os.chmod(directory, 0o700)
    for child in directory.iterdir():
        if child.is_symlink():
            raise RuntimeError("Symlinks are not permitted in Gateway TLS material")
        if child.is_file():
            os.chmod(child, 0o600)


def _run_openssl(*arguments: str) -> None:
    try:
        subprocess.run(
            ("/usr/bin/openssl", *arguments),
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            env={"PATH": "/usr/bin:/bin"},
        )
    except (OSError, subprocess.SubprocessError) as err:
        raise RuntimeError("OpenSSL failed while preparing Gateway TLS material") from err


def _read_ca_certificate(path: Path) -> str:
    if path.is_symlink():
        raise RuntimeError("Gateway CA certificate must not be a symlink")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_CA_CERTIFICATE_BYTES:
        raise RuntimeError("Gateway CA certificate is empty or too large")
    try:
        value = raw.decode("ascii").strip() + "\n"
    except UnicodeDecodeError as err:
        raise RuntimeError("Gateway CA certificate is not ASCII PEM") from err
    if "PRIVATE KEY" in value or value.count("-----BEGIN CERTIFICATE-----") != 1:
        raise RuntimeError("Gateway CA certificate PEM is invalid")
    return value


def _certificate_sha256(pem: str) -> str:
    try:
        der = ssl.PEM_cert_to_DER_cert(pem)
    except ValueError as err:
        raise RuntimeError("Gateway CA certificate PEM is invalid") from err
    return hashlib.sha256(der).hexdigest()


def _read_small_text(path: Path, maximum: int) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise RuntimeError("Gateway TLS metadata is invalid")
    try:
        return path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError) as err:
        raise RuntimeError("Gateway TLS metadata is invalid") from err


def _normalise_hostname(value: Any) -> str:
    if not isinstance(value, str):
        raise RuntimeError("Supervisor app hostname is missing")
    hostname = value.strip().lower().rstrip(".")
    if _HOSTNAME_RE.fullmatch(hostname) is None:
        raise RuntimeError("Supervisor app hostname is invalid")
    return hostname


def _normalise_provider_id(value: str) -> str:
    if not isinstance(value, str) or _PROVIDER_RE.fullmatch(value) is None:
        raise RuntimeError("Gateway provider ID is invalid")
    return value
