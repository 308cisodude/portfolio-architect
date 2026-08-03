"""Private persistence for the bounded two-evaluation decision trace."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .decision_trace import DecisionTraceError, EvaluationHistory, MAX_TRACE_BYTES

_STORAGE_VERSION = 1
_DOCUMENT_VERSION = 1


class DecisionTraceStore:
    """Persist exactly two validated, provider-neutral evaluation snapshots."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store[dict[str, Any]](
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.decision_trace.{entry_id}",
            private=True,
            atomic_writes=True,
            serialize_in_event_loop=False,
        )

    async def async_load(self) -> EvaluationHistory | None:
        try:
            raw = await self._store.async_load()
        except Exception:
            return None
        try:
            if not isinstance(raw, dict) or set(raw) != {
                "document_version",
                "history",
                "history_sha256",
            }:
                return None
            if raw["document_version"] != _DOCUMENT_VERSION:
                return None
            encoded = json.dumps(
                raw,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            if not encoded or len(encoded) > MAX_TRACE_BYTES:
                return None
            history_sha256 = raw["history_sha256"]
            if (
                not isinstance(history_sha256, str)
                or len(history_sha256) != 64
                or any(char not in "0123456789abcdef" for char in history_sha256)
                or history_sha256 != _history_sha256(raw["history"])
            ):
                return None
            return EvaluationHistory.from_dict(raw["history"])
        except (DecisionTraceError, TypeError, ValueError, OverflowError):
            return None

    async def async_save(self, history: EvaluationHistory) -> None:
        history_document = history.to_dict()
        document: dict[str, Any] = {
            "document_version": _DOCUMENT_VERSION,
            "history": history_document,
            "history_sha256": _history_sha256(history_document),
        }
        encoded = json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if not encoded or len(encoded) > MAX_TRACE_BYTES:
            raise ValueError("Decision-trace document exceeds the storage limit")
        await self._store.async_save(document)


def _history_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if not encoded or len(encoded) > MAX_TRACE_BYTES:
        raise ValueError("Decision-trace history exceeds the storage limit")
    return hashlib.sha256(encoded).hexdigest()
