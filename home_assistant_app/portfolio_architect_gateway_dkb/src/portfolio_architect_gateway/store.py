"""Atomic local state persistence with restrictive permissions."""

from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile
from typing import Any

from .errors import ProtocolError
from .models import PortfolioSnapshot, parse_snapshot_bytes, validate_snapshot

MAX_STATE_BYTES = 64 * 1024


def atomic_write(path: Path, data: bytes, *, mode: int = 0o600) -> None:
    """Atomically replace a local state file and fsync both file and directory."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def save_snapshot(path: Path, snapshot: PortfolioSnapshot) -> None:
    atomic_write(path, validate_snapshot(snapshot).to_bytes())


def load_snapshot(path: Path) -> PortfolioSnapshot | None:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as err:
        raise ProtocolError("Cannot read the cached portfolio snapshot") from err
    return parse_snapshot_bytes(data)


def save_json_state(path: Path, value: dict[str, Any]) -> None:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(data) > MAX_STATE_BYTES:
        raise ProtocolError("Session state exceeds the 64 KiB limit")
    atomic_write(path, data)


def load_json_state(path: Path) -> dict[str, Any] | None:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as err:
        raise ProtocolError("Cannot read session state") from err
    if not data or len(data) > MAX_STATE_BYTES:
        raise ProtocolError("Session state is empty or too large")
    try:
        raw = json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError, ProtocolError) as err:
        raise ProtocolError("Session state is invalid") from err
    if not isinstance(raw, dict):
        raise ProtocolError("Session state must be a JSON object")
    return raw


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("Session state contains a duplicate JSON key")
        result[key] = value
    return result
