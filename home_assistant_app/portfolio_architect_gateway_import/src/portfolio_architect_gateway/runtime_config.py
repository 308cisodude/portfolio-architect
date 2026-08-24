"""Provider-neutral local server configuration and secret-file handling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import stat
import tempfile
from typing import Final

from .errors import ConfigurationError

MAX_SECRET_BYTES: Final = 4096
_SECRET_RE = re.compile(r"^[^\x00-\x1f\x7f]+$")


@dataclass(frozen=True, slots=True)
class ServerConfig:
    """Local HTTP server configuration shared by every provider App."""

    bind: str
    port: int
    api_token_file: Path
    snapshot_file: Path
    max_cached_snapshot_age_seconds: int
    tls_cert_file: Path | None
    tls_key_file: Path | None
    health_endpoint_enabled: bool


def normalise_secret(value: str, *, name: str, minimum: int = 1, maximum: int = 4096) -> str:
    """Validate one in-memory secret without logging or transforming it."""
    if not isinstance(value, str):
        raise ConfigurationError(f"Secret for {name} must be text")
    if not minimum <= len(value) <= maximum or _SECRET_RE.fullmatch(value) is None:
        raise ConfigurationError(f"Secret for {name} has an invalid length or characters")
    return value


def read_secret(path: Path, *, name: str, minimum: int = 1, maximum: int = 4096) -> str:
    """Read one bounded secret and reject group/world-readable regular files."""
    try:
        st = path.stat()
    except OSError as err:
        raise ConfigurationError(f"Cannot access secret file for {name}: {path}") from err
    if st.st_size > MAX_SECRET_BYTES:
        raise ConfigurationError(f"Secret file for {name} is too large")
    if stat.S_ISREG(st.st_mode):
        broad = st.st_mode & (stat.S_IRWXG | stat.S_IRWXO)
        writable = st.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        docker_secret = path.is_relative_to(Path("/run/secrets"))
        if writable or (broad and not docker_secret):
            raise ConfigurationError(
                f"Secret file for {name} has unsafe group or other permissions"
            )
    try:
        value = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as err:
        raise ConfigurationError(f"Cannot read secret file for {name}") from err
    if value.endswith("\n"):
        value = value[:-1]
    if value.endswith("\r"):
        value = value[:-1]
    return normalise_secret(value, name=name, minimum=minimum, maximum=maximum)


def atomic_secret(path: Path, value: str, *, name: str, maximum: int) -> None:
    """Persist one secret atomically with mode 0600 in private App storage."""
    cleaned = normalise_secret(value, name=name, maximum=maximum)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", closefd=True) as handle:
            handle.write(cleaned)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def ensure_api_token(path: Path) -> str:
    """Return a stable App-local API token, creating it with mode 0600 once."""
    if path.exists():
        value = path.read_text(encoding="utf-8")
        return normalise_secret(value, name="gateway API token", minimum=32, maximum=512)
    import secrets

    value = secrets.token_urlsafe(48)
    atomic_secret(path, value, name="gateway API token", maximum=512)
    return value
