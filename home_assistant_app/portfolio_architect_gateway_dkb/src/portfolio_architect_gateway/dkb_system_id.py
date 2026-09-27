"""App-private, backup-excluded bank system ID for bounded FinTS research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import re
import stat

from .errors import ProtocolError
from .store import atomic_write, load_json_state

FILE_NAME = "dkb-fints-system-id.json"
MAX_AGE = timedelta(hours=72)
MAX_BYTES = 512
_ID = re.compile(r"[A-Za-z0-9]{1,64}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True, slots=True)
class SystemIdRecord:
    system_id: str
    seeded_at: datetime


def binding(product_id: str, user_id: str) -> str:
    return hashlib.sha256((product_id + "\0" + user_id).encode("utf-8")).hexdigest()


def _valid_time(value: object) -> datetime | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        result = datetime.fromisoformat(value)
    except ValueError:
        return None
    if result.tzinfo is None or result.utcoffset() is None:
        return None
    return result.astimezone(timezone.utc)


def load(path: Path, identity: str, now: datetime | None = None) -> SystemIdRecord | None:
    """Fail closed for missing, malformed, expired or different-user state."""
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    try:
        details = path.lstat()
        if (not stat.S_ISREG(details.st_mode) or details.st_mode & 0o077
                or details.st_size > MAX_BYTES or details.st_size == 0):
            raise ValueError("invalid system ID file")
        raw = load_json_state(path)
        if raw is None or set(raw) != {"schema_version", "binding", "system_id", "seeded_at"}:
            raise ValueError("invalid system ID schema")
        if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
            raise ValueError("invalid system ID schema version")
        if not isinstance(raw["binding"], str) or not _DIGEST.fullmatch(raw["binding"]):
            raise ValueError("invalid system ID binding")
        value = raw["system_id"]
        if not isinstance(value, str) or value == "0" or not _ID.fullmatch(value):
            raise ValueError("invalid system ID")
        seeded_at = _valid_time(raw["seeded_at"])
        if seeded_at is None or not timedelta(0) <= current - seeded_at < MAX_AGE:
            raise ValueError("expired system ID")
        if raw["binding"] != identity:
            return None
        return SystemIdRecord(value, seeded_at)
    except FileNotFoundError:
        return None
    except (OSError, ValueError, TypeError, ProtocolError):
        # A corrupt or expired research hint cannot prevent a fresh bank login.
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return None


def save(path: Path, identity: str, system_id: str, seeded_at: datetime) -> None:
    if not _DIGEST.fullmatch(identity) or system_id == "0" or not _ID.fullmatch(system_id):
        raise ValueError("invalid bounded system ID record")
    if seeded_at.tzinfo is None or seeded_at.utcoffset() is None:
        raise ValueError("invalid system ID timestamp")
    timestamp = seeded_at.astimezone(timezone.utc).isoformat(timespec="seconds")
    data = (f'{{"schema_version":1,"binding":"{identity}",'
            f'"system_id":"{system_id}","seeded_at":"{timestamp}"}}').encode("ascii")
    if len(data) > MAX_BYTES:
        raise ValueError("system ID record exceeds limit")
    atomic_write(path, data)
