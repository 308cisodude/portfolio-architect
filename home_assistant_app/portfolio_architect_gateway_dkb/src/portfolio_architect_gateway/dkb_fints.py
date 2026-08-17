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
DEFAULT_TIMEOUT_SECONDS: Final = 20

_PRODUCT_ID_RE = re.compile(r"^[A-Za-z0-9]{1,25}$")
_SEGMENT_HEADER_RE = re.compile(rb"^([A-Z][A-Z0-9]{1,5}):(\d{1,3}):(\d{1,3})(?::\d{1,3})?$")
_PARAMETER_SEGMENT_RE = re.compile(r"^HI[A-Z0-9]{3}S$")
_RETURN_CODE_RE = re.compile(rb"(?:^|\+)(\d{4}):")


@dataclass(frozen=True, slots=True)
class SegmentSummary:
    """Bounded FinTS segment header without payload data."""

    type: str
    number: int
    version: int


@dataclass(frozen=True, slots=True)
class CapabilityProbeResult:
    """Sanitized anonymous BPD capability-probe result."""

    probed_at: str
    bpd_version: int | None
    parameter_segments: tuple[str, ...]
    return_codes: tuple[str, ...]
    holdings_advertised: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "probed_at": self.probed_at,
            "bpd_version": self.bpd_version,
            "parameter_segments": list(self.parameter_segments),
            "return_codes": list(self.return_codes),
            "holdings_advertised": self.holdings_advertised,
        }


def normalise_product_id(value: str) -> str:
    """Validate a FinTS product registration number for safe wire use."""
    if not isinstance(value, str):
        raise ValueError("FinTS product registration number must be text")
    token = value.strip()
    if _PRODUCT_ID_RE.fullmatch(token) is None:
        raise ValueError("FinTS product registration number must be 1-25 alphanumeric characters")
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
                "User-Agent": "PortfolioArchitect-DKB/1.31.1",
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
    return parse_capability_response(payload)


def parse_capability_response(payload: bytes, *, now: datetime | None = None) -> CapabilityProbeResult:
    """Reduce a FinTS institute response to non-private BPD capability metadata."""
    segments = _split_segments(payload)
    summaries: list[SegmentSummary] = []
    parameter_segments: set[str] = set()
    return_codes: list[str] = []
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
            for code in _RETURN_CODE_RE.findall(b"+" + body):
                value = code.decode("ascii")
                if value not in return_codes:
                    if len(return_codes) >= MAX_RETURN_CODES:
                        raise ProtocolError("FinTS response contains too many return codes")
                    return_codes.append(value)

    if not summaries or summaries[0].type != "HNHBK" or summaries[-1].type != "HNHBS":
        raise ProtocolError("FinTS response does not contain a complete message envelope")
    if bpd_version is None:
        raise ProtocolError("FinTS response does not contain bank-parameter data")
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    ordered_parameters = tuple(sorted(parameter_segments))
    return CapabilityProbeResult(
        probed_at=timestamp,
        bpd_version=bpd_version,
        parameter_segments=ordered_parameters,
        return_codes=tuple(return_codes),
        holdings_advertised=HOLDINGS_PARAMETER_SEGMENT in parameter_segments,
    )


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
