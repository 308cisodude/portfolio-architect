"""Private Home Assistant-side last-known-good cache for REST calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .cache_payload import json_safe_payload
from .const import DOMAIN

_CACHE_STORAGE_VERSION = 1
_CACHE_DOCUMENT_VERSION = 1
_MAX_CACHE_BYTES = 4 * 1024 * 1024
_SHA256_LENGTH = 64


@dataclass(frozen=True, slots=True)
class RestLastKnownGood:
    """One validated calculated payload restored from private HA storage."""

    payload: dict[str, Any]
    endpoint_url: str
    configuration_sha256: str
    snapshot_generated_at: datetime
    snapshot_sha256: str | None
    snapshot_position_count: int | None
    saved_at: datetime


class RestLastKnownGoodStore:
    """Persist only an already validated calculated payload and integrity metadata."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(
            hass,
            _CACHE_STORAGE_VERSION,
            f"{DOMAIN}.last_known_good.{entry_id}",
            private=True,
            atomic_writes=True,
            serialize_in_event_loop=False,
        )

    async def async_load(
        self,
        *,
        endpoint_url: str,
        configuration_sha256: str,
    ) -> RestLastKnownGood | None:
        """Load and strictly validate one cache document for the current source."""
        try:
            raw = await self._store.async_load()
        except Exception:
            return None
        try:
            if not isinstance(raw, dict) or set(raw) != {
                "cache_document_version",
                "endpoint_url",
                "configuration_sha256",
                "snapshot_generated_at",
                "snapshot_sha256",
                "snapshot_position_count",
                "saved_at",
                "payload",
            }:
                return None
            if raw["cache_document_version"] != _CACHE_DOCUMENT_VERSION:
                return None
            if raw["endpoint_url"] != endpoint_url:
                return None
            if raw["configuration_sha256"] != configuration_sha256:
                return None
            payload = raw["payload"]
            if not isinstance(payload, dict):
                return None
            encoded = json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            if not encoded or len(encoded) > _MAX_CACHE_BYTES:
                return None
            generated_at = _parse_utc_datetime(raw["snapshot_generated_at"])
            saved_at = _parse_utc_datetime(raw["saved_at"])
            digest = _optional_sha256(raw["snapshot_sha256"])
            position_count = _optional_position_count(raw["snapshot_position_count"])
        except (TypeError, ValueError, OverflowError):
            return None
        return RestLastKnownGood(
            payload=dict(payload),
            endpoint_url=endpoint_url,
            configuration_sha256=configuration_sha256,
            snapshot_generated_at=generated_at,
            snapshot_sha256=digest,
            snapshot_position_count=position_count,
            saved_at=saved_at,
        )

    async def async_save(
        self,
        *,
        payload: dict[str, Any],
        endpoint_url: str,
        configuration_sha256: str,
        snapshot_generated_at: datetime,
        snapshot_sha256: str | None,
        snapshot_position_count: int | None,
    ) -> None:
        """Atomically save a bounded copy of one fully validated calculation."""
        payload_copy = json_safe_payload(payload)
        encoded = json.dumps(
            payload_copy,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if not encoded or len(encoded) > _MAX_CACHE_BYTES:
            raise ValueError("Calculated last-known-good payload exceeds the cache limit")
        document = {
            "cache_document_version": _CACHE_DOCUMENT_VERSION,
            "endpoint_url": endpoint_url,
            "configuration_sha256": _sha256(configuration_sha256),
            "snapshot_generated_at": _utc_iso(snapshot_generated_at),
            "snapshot_sha256": _optional_sha256(snapshot_sha256),
            "snapshot_position_count": _optional_position_count(snapshot_position_count),
            "saved_at": _utc_iso(datetime.now(timezone.utc)),
            "payload": payload_copy,
        }
        await self._store.async_save(document)


def configuration_fingerprint(
    config_directory: Path,
    configuration_paths: tuple[Path, ...],
    plan_override: dict[str, Any] | None,
) -> str:
    """Return a stable digest for every calculation input except live positions."""
    digest = hashlib.sha256()
    for path in sorted(configuration_paths, key=lambda item: item.name):
        if not path.is_file():
            raise ValueError("Portfolio configuration files are unavailable")
        relative = path.relative_to(config_directory).as_posix().encode("utf-8")
        body = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(body).to_bytes(8, "big"))
        digest.update(body)
    override = json.dumps(
        plan_override,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest.update(len(override).to_bytes(8, "big"))
    digest.update(override)
    return digest.hexdigest()


def _parse_utc_datetime(value: Any) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("Cached timestamp is invalid")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Cached timestamp lacks a timezone")
    return parsed.astimezone(timezone.utc)


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Cache timestamp lacks a timezone")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _optional_sha256(value: Any) -> str | None:
    if value is None:
        return None
    return _sha256(value)


def _sha256(value: Any) -> str:
    if (
        not isinstance(value, str)
        or len(value) != _SHA256_LENGTH
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError("Cached SHA-256 value is invalid")
    return value


def _optional_position_count(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 512:
        raise ValueError("Cached position count is invalid")
    return value
