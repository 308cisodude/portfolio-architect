"""Minimal read-only DKB FinTS capability probe.

This module intentionally implements only an anonymous FinTS 3.0 dialog
initialization against DKB's fixed endpoint.  It does not contain user/PIN/TAN
handling or any business-transaction request.  The response is reduced to
bounded capability metadata and the raw response is discarded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import binascii
import http.client
import hashlib
import re
import ssl
from typing import Final

from .errors import ProtocolError, RemoteApiError

DKB_FINTS_HOST: Final = "fints.dkb.de"
DKB_FINTS_PATH: Final = "/fints"
DKB_FINTS_ENDPOINT: Final = f"https://{DKB_FINTS_HOST}{DKB_FINTS_PATH}"
DKB_BANK_CODE: Final = "12030000"
FINTS_COUNTRY_CODE_DE: Final = "280"
FINTS_VERSION: Final = "300"
ANONYMOUS_CUSTOMER_ID: Final = "9999999999"
ANONYMOUS_SYSTEM_ID: Final = "0"
ANONYMOUS_SYSTEM_ID_STATUS: Final = "0"
FINTS_LANGUAGE_DE: Final = "1"
# HKVVB's product-version field is limited to five characters in FinTS 3.0.
FINTS_PRODUCT_VERSION: Final = "1.28"
HOLDINGS_PARAMETER_SEGMENT: Final = "HIWPDS"
MAX_RESPONSE_BYTES: Final = 1024 * 1024
MAX_BASE64_RESPONSE_BYTES: Final = ((MAX_RESPONSE_BYTES + 2) // 3) * 4 + 16
MAX_SEGMENTS: Final = 256
MAX_PARAMETER_SEGMENTS: Final = 128
MAX_RETURN_CODES: Final = 32
MAX_RETURN_MESSAGES: Final = 32
MAX_RETURN_MESSAGE_CHARS: Final = 256
DEFAULT_TIMEOUT_SECONDS: Final = 20

_PRODUCT_ID_RE = re.compile(r"^[A-Za-z0-9]{25}$")
_SEGMENT_HEADER_RE = re.compile(rb"^([A-Z][A-Z0-9]{1,5}):(\d{1,3}):(\d{1,3})(?::\d{1,3})?$")
_PARAMETER_SEGMENT_RE = re.compile(r"^HI[A-Z0-9]{3}S$")


@dataclass(frozen=True, slots=True)
class SegmentSummary:
    """Bounded FinTS segment header without payload data."""

    type: str
    number: int
    version: int


@dataclass(frozen=True, slots=True)
class ReturnMessage:
    """Bounded sanitized HIRMG/HIRMS return-message evidence."""

    code: str
    text: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "text": self.text}


@dataclass(frozen=True, slots=True)
class CapabilityProbeResult:
    """Sanitized anonymous BPD capability-probe result or bounded failure evidence."""

    probed_at: str
    bpd_version: int | None
    parameter_segments: tuple[str, ...]
    return_codes: tuple[str, ...]
    holdings_advertised: bool | None
    outcome: str = "complete"
    failure_category: str | None = None
    http_status: int | None = None
    return_messages: tuple[ReturnMessage, ...] = ()
    response_sha256: str | None = None
    response_bytes: int | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 2,
            "probed_at": self.probed_at,
            "outcome": self.outcome,
            "failure_category": self.failure_category,
            "http_status": self.http_status,
            "bpd_version": self.bpd_version,
            "parameter_segments": list(self.parameter_segments),
            "return_codes": list(self.return_codes),
            "return_messages": [message.as_dict() for message in self.return_messages],
            "response_sha256": self.response_sha256,
            "response_bytes": self.response_bytes,
            "holdings_advertised": self.holdings_advertised,
        }


def normalise_product_id(value: str) -> str:
    """Validate a FinTS product registration number for safe wire use."""
    if not isinstance(value, str):
        raise ValueError("FinTS product registration number must be text")
    token = value.strip()
    if _PRODUCT_ID_RE.fullmatch(token) is None:
        raise ValueError("FinTS product registration number must be exactly 25 alphanumeric characters")
    return token


def build_anonymous_bpd_request(product_id: str) -> bytes:
    """Build one FinTS 3.0 anonymous dialog initialization requesting current BPD."""
    product = normalise_product_id(product_id)
    segments = (
        "HNHBK:1:3+{size}+300+0+1'"
        f"HKIDN:2:2+{FINTS_COUNTRY_CODE_DE}:{DKB_BANK_CODE}+{ANONYMOUS_CUSTOMER_ID}+{ANONYMOUS_SYSTEM_ID}+{ANONYMOUS_SYSTEM_ID_STATUS}'"
        f"HKVVB:3:3+0+0+{FINTS_LANGUAGE_DE}+{product}+{FINTS_PRODUCT_VERSION}'"
        "HNHBS:4:1+1'"
    )
    # The FinTS message-size field is exactly twelve decimal digits, so replacing
    # the placeholder with another 12-byte value does not change the total size.
    placeholder = "000000000000"
    payload = segments.format(size=placeholder).encode("iso-8859-1")
    size = f"{len(payload):012d}"
    return segments.format(size=size).encode("iso-8859-1")


def probe_dkb_bpd(product_id: str, *, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> CapabilityProbeResult:
    """Perform one fixed-endpoint anonymous DKB BPD probe and discard raw bank data."""
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 5 <= timeout_seconds <= 60:
        raise ValueError("FinTS request timeout is outside the supported range")
    request = build_anonymous_bpd_request(product_id)
    encoded = base64.b64encode(request)
    context = ssl.create_default_context()
    connection = http.client.HTTPSConnection(
        DKB_FINTS_HOST,
        443,
        timeout=timeout_seconds,
        context=context,
    )
    try:
        connection.request(
            "POST",
            DKB_FINTS_PATH,
            body=encoded,
            headers={
                "Content-Type": "text/plain",
                "Content-Length": str(len(encoded)),
                "User-Agent": "PortfolioArchitect-DKB/1.33.1",
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        if response.status < 200 or response.status > 299:
            response.read(min(MAX_BASE64_RESPONSE_BYTES, 8192))
            raise RemoteApiError(response.status, "DKB FinTS endpoint returned a non-success status", operation="fints_bpd_probe")
        encoded_response = response.read(MAX_BASE64_RESPONSE_BYTES + 1)
        if len(encoded_response) > MAX_BASE64_RESPONSE_BYTES:
            raise ProtocolError("DKB FinTS response exceeds the bounded size limit")
    except (OSError, ssl.SSLError, http.client.HTTPException) as err:
        raise RemoteApiError(0, "DKB FinTS transport failed", operation="fints_bpd_probe") from err
    finally:
        connection.close()
    try:
        payload = base64.b64decode(encoded_response.strip(), validate=True)
    except (binascii.Error, ValueError) as err:
        raise ProtocolError("DKB FinTS response is not valid base64") from err
    if not payload or len(payload) > MAX_RESPONSE_BYTES:
        raise ProtocolError("DKB FinTS response is empty or too large")
    try:
        return parse_capability_response(payload, redact_tokens=(product_id,))
    except ProtocolError as err:
        # Preserve only a correlation fingerprint/length for malformed decoded FinTS
        # responses. Raw response bytes and parse-error detail remain ephemeral.
        err.response_sha256 = hashlib.sha256(payload).hexdigest()
        err.response_bytes = len(payload)
        raise


def parse_capability_response(
    payload: bytes,
    *,
    now: datetime | None = None,
    redact_tokens: tuple[str, ...] = (),
) -> CapabilityProbeResult:
    """Reduce a FinTS institute response to bounded non-private diagnostic evidence."""
    segments = _split_segments(payload)
    summaries: list[SegmentSummary] = []
    parameter_segments: set[str] = set()
    return_codes: list[str] = []
    return_messages: list[ReturnMessage] = []
    bpd_version: int | None = None

    for index, segment in enumerate(segments):
        header, separator, body = segment.partition(b"+")
        if not separator:
            raise ProtocolError("FinTS segment is missing its data delimiter")
        match = _SEGMENT_HEADER_RE.fullmatch(header)
        if match is None:
            raise ProtocolError("FinTS segment header is invalid")
        segment_type = match.group(1).decode("ascii")
        summary = SegmentSummary(segment_type, int(match.group(2)), int(match.group(3)))
        summaries.append(summary)
        if index == 0:
            declared_size, size_separator, _header_rest = body.partition(b"+")
            if not size_separator or len(declared_size) != 12 or not declared_size.isdigit():
                raise ProtocolError("FinTS message header contains an invalid size")
            if int(declared_size) != len(payload):
                raise ProtocolError("FinTS message size does not match the received payload")
        if _PARAMETER_SEGMENT_RE.fullmatch(segment_type):
            if len(parameter_segments) >= MAX_PARAMETER_SEGMENTS and segment_type not in parameter_segments:
                raise ProtocolError("FinTS response contains too many parameter segment types")
            parameter_segments.add(segment_type)
        if segment_type == "HIBPA":
            if bpd_version is not None:
                raise ProtocolError("FinTS response contains duplicate bank parameters")
            first, _, _rest = body.partition(b"+")
            if not first.isdigit() or not 0 < len(first) <= 3:
                raise ProtocolError("FinTS bank-parameter version is invalid")
            bpd_version = int(first)
        if segment_type in {"HIRMG", "HIRMS"}:
            for group in _split_unescaped(body, ord("+")):
                fields = _split_unescaped(group, ord(":"))
                if not fields or len(fields[0]) != 4 or not fields[0].isdigit():
                    continue
                value = fields[0].decode("ascii")
                if value not in return_codes:
                    if len(return_codes) >= MAX_RETURN_CODES:
                        raise ProtocolError("FinTS response contains too many return codes")
                    return_codes.append(value)
                if len(fields) >= 3:
                    text = _sanitize_return_message(fields[2], redact_tokens=redact_tokens)
                    if text:
                        message = ReturnMessage(value, text)
                        if message not in return_messages:
                            if len(return_messages) >= MAX_RETURN_MESSAGES:
                                raise ProtocolError("FinTS response contains too many return messages")
                            return_messages.append(message)

    if not summaries or summaries[0].type != "HNHBK" or summaries[-1].type != "HNHBS":
        raise ProtocolError("FinTS response does not contain a complete message envelope")
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    ordered_parameters = tuple(sorted(parameter_segments))
    response_sha256 = hashlib.sha256(payload).hexdigest()
    response_bytes = len(payload)
    if bpd_version is None:
        if not return_codes:
            raise ProtocolError("FinTS response does not contain bank-parameter data or return codes")
        return CapabilityProbeResult(
            probed_at=timestamp,
            bpd_version=None,
            parameter_segments=ordered_parameters,
            return_codes=tuple(return_codes),
            holdings_advertised=None,
            outcome="bank_rejected",
            failure_category="bank_response_without_bpd",
            return_messages=tuple(return_messages),
            response_sha256=response_sha256,
            response_bytes=response_bytes,
        )
    return CapabilityProbeResult(
        probed_at=timestamp,
        bpd_version=bpd_version,
        parameter_segments=ordered_parameters,
        return_codes=tuple(return_codes),
        holdings_advertised=HOLDINGS_PARAMETER_SEGMENT in parameter_segments,
        return_messages=tuple(return_messages),
        response_sha256=response_sha256,
        response_bytes=response_bytes,
    )


def _split_unescaped(value: bytes, delimiter: int) -> list[bytes]:
    """Split one FinTS field on an unescaped delimiter while retaining escape pairs."""
    parts: list[bytearray] = [bytearray()]
    index = 0
    while index < len(value):
        current = value[index]
        if current == ord("?"):
            if index + 1 >= len(value):
                raise ProtocolError("FinTS return message contains a dangling escape")
            parts[-1].extend(value[index : index + 2])
            index += 2
            continue
        if current == delimiter:
            parts.append(bytearray())
        else:
            parts[-1].append(current)
        index += 1
    return [bytes(part) for part in parts]


def _unescape_fints(value: bytes) -> bytes:
    output = bytearray()
    index = 0
    while index < len(value):
        current = value[index]
        if current == ord("?"):
            if index + 1 >= len(value):
                raise ProtocolError("FinTS return message contains a dangling escape")
            output.append(value[index + 1])
            index += 2
            continue
        output.append(current)
        index += 1
    return bytes(output)


def _sanitize_return_message(value: bytes, *, redact_tokens: tuple[str, ...]) -> str:
    """Return bounded operator-visible bank text without retaining arbitrary fields."""
    text = _unescape_fints(value).decode("iso-8859-1")
    text = "".join(" " if ord(char) < 32 or ord(char) == 127 else char for char in text)
    text = " ".join(text.split())
    for token in redact_tokens:
        if token:
            text = text.replace(token, "[REDACTED_PRODUCT_ID]")
    if len(text) > MAX_RETURN_MESSAGE_CHARS:
        text = text[: MAX_RETURN_MESSAGE_CHARS - 1].rstrip() + "…"
    return text


def _split_segments(payload: bytes) -> list[bytes]:
    """Split FinTS segments while respecting escapes and binary data fields."""
    result: list[bytes] = []
    start = 0
    index = 0
    length = len(payload)
    while index < length:
        value = payload[index]
        if value == 0x3F:  # '?' escape
            index += 2
            continue
        if value == 0x40:  # @<length>@<binary>
            end_digits = payload.find(b"@", index + 1, min(length, index + 16))
            if end_digits == -1:
                raise ProtocolError("FinTS binary field has an invalid length prefix")
            digits = payload[index + 1 : end_digits]
            if not digits.isdigit() or len(digits) > 9:
                raise ProtocolError("FinTS binary field has an invalid length")
            binary_length = int(digits)
            index = end_digits + 1 + binary_length
            if index > length:
                raise ProtocolError("FinTS binary field exceeds the response body")
            continue
        if value == 0x27:  # apostrophe segment terminator
            segment = payload[start:index]
            if not segment:
                raise ProtocolError("FinTS response contains an empty segment")
            result.append(segment)
            if len(result) > MAX_SEGMENTS:
                raise ProtocolError("FinTS response contains too many segments")
            start = index + 1
        index += 1
    if start != length:
        raise ProtocolError("FinTS response ends inside a segment")
    return result
