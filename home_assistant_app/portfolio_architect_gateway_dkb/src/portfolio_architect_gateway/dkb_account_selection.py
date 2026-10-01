"""App-private binding of one DKB EUR balance account to a banking user."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import os
from pathlib import Path
import re
import stat
from typing import Any

from .errors import ProtocolError
from .store import atomic_write, load_json_state, save_json_state

SELECTION_FILE_NAME = "dkb-fints-investment-account.json"
KEY_FILE_NAME = "dkb-fints-account-binding-key"
_IBAN = re.compile(r"DE[0-9]{20}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_SUFFIX = re.compile(r"[0-9]{4}\Z")


@dataclass(frozen=True, slots=True)
class SelectedAccount:
    binding: str
    user_binding: str
    suffix: str

    @property
    def masked_label(self) -> str:
        return f"EUR balance account ending {self.suffix}"


def _key(path: Path, *, create: bool = False) -> bytes:
    try:
        details = path.lstat()
        if not stat.S_ISREG(details.st_mode) or details.st_mode & 0o077 or details.st_size != 32:
            raise ProtocolError("Stored account binding key is invalid")
        value = path.read_bytes()
    except FileNotFoundError:
        if not create:
            raise ProtocolError("Selected account binding key is missing") from None
        value = os.urandom(32)
        atomic_write(path, value)
    if len(value) != 32:
        raise ProtocolError("Stored account binding key is invalid")
    return value


def _digest(key: bytes, label: bytes, *parts: str) -> str:
    if any(not isinstance(part, str) or not part or len(part) > 128 for part in parts):
        raise ValueError("Invalid account binding input")
    return hmac.new(key, label + b"\0" + "\0".join(parts).encode("utf-8"), hashlib.sha256).hexdigest()


def select(path: Path, key_path: Path, *, product_id: str, user_id: str,
           account: dict[str, Any]) -> SelectedAccount:
    iban = account.get("iban")
    number = account.get("account_number")
    bank = account.get("bank_code") or getattr(account.get("bank_identifier"), "bank_code", None)
    if not isinstance(iban, str) or not _IBAN.fullmatch(iban) or not isinstance(number, str) or not number or not isinstance(bank, str) or not bank:
        raise ValueError("Selected account metadata is incomplete")
    key = _key(key_path, create=True)
    value = SelectedAccount(_digest(key, b"dkb-account", iban, number, bank),
                            _digest(key, b"dkb-user", product_id, user_id), iban[-4:])
    save_json_state(path, {"schema_version": 1, "binding": value.binding,
                           "user_binding": value.user_binding, "suffix": value.suffix})
    return value


def load(path: Path, key_path: Path) -> SelectedAccount | None:
    raw = load_json_state(path)
    if raw is None:
        return None
    if (set(raw) != {"schema_version", "binding", "user_binding", "suffix"}
            or type(raw["schema_version"]) is not int or raw["schema_version"] != 1
            or not isinstance(raw["binding"], str) or not _DIGEST.fullmatch(raw["binding"])
            or not isinstance(raw["user_binding"], str) or not _DIGEST.fullmatch(raw["user_binding"])
            or not isinstance(raw["suffix"], str) or not _SUFFIX.fullmatch(raw["suffix"])):
        raise ProtocolError("Stored DKB account selection is invalid")
    _key(key_path)
    return SelectedAccount(raw["binding"], raw["user_binding"], raw["suffix"])


def matches(value: SelectedAccount, key_path: Path, *, product_id: str,
            user_id: str, account: dict[str, Any]) -> bool:
    iban = account.get("iban")
    number = account.get("account_number")
    bank = account.get("bank_code") or getattr(account.get("bank_identifier"), "bank_code", None)
    if (not isinstance(iban, str) or not _IBAN.fullmatch(iban) or
            not isinstance(number, str) or not number or not isinstance(bank, str) or not bank):
        return False
    key = _key(key_path)
    return (hmac.compare_digest(value.user_binding, _digest(key, b"dkb-user", product_id, user_id))
            and hmac.compare_digest(value.binding, _digest(key, b"dkb-account", iban, number, bank)))


def user_matches(value: SelectedAccount, key_path: Path, *, product_id: str, user_id: str) -> bool:
    return hmac.compare_digest(value.user_binding,
                               _digest(_key(key_path), b"dkb-user", product_id, user_id))
