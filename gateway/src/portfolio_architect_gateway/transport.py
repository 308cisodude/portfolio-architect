"""Bounded HTTPS transport for the small Comdirect endpoint allowlist."""

from __future__ import annotations

from dataclasses import dataclass
from http.cookiejar import Cookie, CookieJar
import json
import secrets
import socket
import ssl
import time
from threading import Lock
from typing import Any, Final, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    HTTPSHandler,
    Request,
    build_opener,
)

from .errors import ProtocolError, RemoteApiError

MAX_REMOTE_RESPONSE_BYTES: Final = 2 * 1024 * 1024
MAX_REMOTE_HEADER_BYTES: Final = 64 * 1024
USER_AGENT: Final = "portfolio-architect-gateway/1.18.0"


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Sanitized response data retained by the client."""

    status: int
    body: bytes
    headers: Mapping[str, str]


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class ComdirectTransport:
    """HTTPS client exposing only authentication/session and read endpoints."""

    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._cookies = CookieJar()
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        self._opener = build_opener(
            _NoRedirects(), HTTPCookieProcessor(self._cookies), HTTPSHandler(context=context)
        )
        # Comdirect requires a 32-character hexadecimal client session ID and
        # a unique nine-digit decimal request ID for each API request.
        self._client_session_id = secrets.token_hex(16)
        self._request_id_lock = Lock()
        self._request_id = secrets.randbelow(1_000_000_000)

    def restore_qsession(self, value: str | None) -> None:
        if not value:
            return
        if len(value) > 2048 or any(ord(ch) < 33 or ord(ch) > 126 for ch in value):
            raise ProtocolError("Persisted qSession cookie is invalid")
        self._cookies.set_cookie(
            Cookie(
                version=0,
                name="qSession",
                value=value,
                port=None,
                port_specified=False,
                domain=".comdirect.de",
                domain_specified=True,
                domain_initial_dot=True,
                path="/",
                path_specified=True,
                secure=True,
                expires=None,
                discard=True,
                comment=None,
                comment_url=None,
                rest={"HttpOnly": None},
                rfc2109=False,
            )
        )

    def current_qsession(self) -> str | None:
        for cookie in self._cookies:
            if cookie.name == "qSession":
                return cookie.value
        return None

    def oauth_password(
        self,
        *,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
    ) -> HttpResponse:
        return self._request_form(
            "/oauth/token",
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "password",
                "username": username,
                "password": password,
            },
            operation="oauth_password",
        )

    def oauth_secondary(
        self,
        *,
        client_id: str,
        client_secret: str,
        initial_access_token: str,
    ) -> HttpResponse:
        return self._request_form(
            "/oauth/token",
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "cd_secondary",
                "token": initial_access_token,
            },
            bearer=initial_access_token,
            operation="oauth_secondary",
        )

    def oauth_refresh(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> HttpResponse:
        return self._request_form(
            "/oauth/token",
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            operation="oauth_refresh",
        )

    def get_sessions(self, *, bearer: str) -> HttpResponse:
        return self._request_json(
            "GET",
            "/api/session/clients/user/v1/sessions",
            bearer=bearer,
            operation="get_sessions",
        )

    def validate_session(
        self, *, session_id: str, session_document: dict[str, Any], bearer: str
    ) -> HttpResponse:
        path = (
            "/api/session/clients/user/v1/sessions/"
            f"{quote(_path_token(session_id), safe='')}/validate"
        )
        return self._request_json(
            "POST",
            path,
            bearer=bearer,
            json_document=session_document,
            operation="validate_session",
        )

    def activate_session(
        self,
        *,
        session_id: str,
        session_document: dict[str, Any],
        bearer: str,
        once_authentication_info: str,
        once_authentication: str | None,
    ) -> HttpResponse:
        path = (
            "/api/session/clients/user/v1/sessions/"
            f"{quote(_path_token(session_id), safe='')}"
        )
        headers = {"x-once-authentication-info": once_authentication_info}
        if once_authentication:
            headers["x-once-authentication"] = once_authentication
        return self._request_json(
            "PATCH",
            path,
            bearer=bearer,
            json_document=session_document,
            extra_headers=headers,
            operation="activate_session",
        )

    def poll_session_challenge(self, *, href: str, bearer: str) -> HttpResponse:
        parsed = urlsplit(urljoin(f"{self._base_url}/", href))
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.comdirect.de"
            or parsed.port not in (None, 443)
            or not parsed.path.startswith("/api/session/")
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ProtocolError("Comdirect returned an unsafe MFA polling URL")
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        return self._request_json(
            "GET", path, bearer=bearer, operation="poll_session_challenge"
        )


    def get_account_balances(self, *, bearer: str) -> HttpResponse:
        return self._request_json(
            "GET",
            "/api/banking/clients/user/v2/accounts/balances?with-attr=true",
            bearer=bearer,
            operation="get_account_balances",
        )

    def get_depots(self, *, bearer: str) -> HttpResponse:
        return self._request_json(
            "GET",
            "/api/brokerage/clients/user/v3/depots",
            bearer=bearer,
            operation="get_depots",
        )

    def get_positions(
        self, *, depot_id: str, first: int, count: int, bearer: str
    ) -> HttpResponse:
        if not 0 <= first <= 100000 or not 1 <= count <= 1000:
            raise ProtocolError("Position paging request is outside the allowed range")
        path = (
            f"/api/brokerage/v3/depots/{quote(_path_token(depot_id), safe='')}/positions?"
            + urlencode({"paging-first": first, "paging-count": count})
        )
        return self._request_json(
            "GET", path, bearer=bearer, operation="get_positions"
        )

    def get_instrument(self, *, instrument_id: str, bearer: str) -> HttpResponse:
        path = (
            "/api/brokerage/v1/instruments/"
            f"{quote(_path_token(instrument_id), safe='')}"
        )
        return self._request_json(
            "GET", path, bearer=bearer, operation="get_instrument"
        )

    def _request_form(
        self,
        path: str,
        form: dict[str, str],
        *,
        bearer: str | None = None,
        operation: str,
    ) -> HttpResponse:
        data = urlencode(form).encode("ascii")
        return self._request(
            "POST",
            path,
            data=data,
            bearer=bearer,
            content_type="application/x-www-form-urlencoded",
            operation=operation,
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        bearer: str,
        json_document: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        operation: str,
    ) -> HttpResponse:
        data = None
        content_type = None
        if json_document is not None:
            data = json.dumps(
                json_document, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            if len(data) > 64 * 1024:
                raise ProtocolError("Outbound JSON request exceeds the safety limit")
            content_type = "application/json"
        return self._request(
            method,
            path,
            data=data,
            bearer=bearer,
            content_type=content_type,
            extra_headers=extra_headers,
            operation=operation,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None,
        bearer: str | None,
        content_type: str | None,
        extra_headers: dict[str, str] | None = None,
        operation: str,
    ) -> HttpResponse:
        if method not in {"GET", "POST", "PATCH"}:
            raise ProtocolError("Unsupported outbound HTTP method")
        if not path.startswith("/") or "\r" in path or "\n" in path:
            raise ProtocolError("Invalid outbound API path")
        url = f"{self._base_url}{path}"
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "api.comdirect.de":
            raise ProtocolError("Outbound request escaped the Comdirect API origin")

        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "x-http-request-info": json.dumps(
                {
                    "clientRequestId": {
                        "sessionId": self._client_session_id,
                        "requestId": self._next_request_id(),
                    }
                },
                separators=(",", ":"),
            ),
        }
        if bearer:
            _validate_opaque_token(bearer, "access token")
            headers["Authorization"] = f"Bearer {bearer}"
        if content_type:
            headers["Content-Type"] = content_type
        if extra_headers:
            for key, value in extra_headers.items():
                if key.lower() not in {
                    "x-once-authentication",
                    "x-once-authentication-info",
                }:
                    raise ProtocolError("Unsupported additional outbound HTTP header")
                _validate_header_value(value, key)
                headers[key] = value

        request = Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                response_headers = _bounded_headers(response.headers.items())
                body = _read_bounded(response, MAX_REMOTE_RESPONSE_BYTES)
                return HttpResponse(
                    status=int(response.status), body=body, headers=response_headers
                )
        except HTTPError as err:
            # Redirects arrive here because redirects are intentionally disabled.
            retry_after = _parse_retry_after(err.headers.get("Retry-After"))
            status = int(err.code)
            error_code = None
            if operation.startswith("oauth_"):
                error_body = _read_error_body_bounded(err, 64 * 1024)
                error_code = _oauth_error_code(
                    error_body, err.headers.get("Content-Type")
                )
            else:
                _drain_bounded(err, MAX_REMOTE_RESPONSE_BYTES)
            raise RemoteApiError(
                status,
                f"Comdirect API returned HTTP {status}",
                retry_after=retry_after,
                operation=operation,
                error_code=error_code,
            ) from None
        except (URLError, TimeoutError, socket.timeout, ssl.SSLError) as err:
            raise RemoteApiError(
                0,
                "Comdirect API transport failed",
                operation=operation,
            ) from err

    def _next_request_id(self) -> str:
        """Return a unique nine-digit decimal ID for the client session."""
        with self._request_id_lock:
            value = self._request_id
            self._request_id = (self._request_id + 1) % 1_000_000_000
        return f"{value:09d}"


def decode_json_response(response: HttpResponse) -> Any:
    """Decode strict UTF-8 JSON and reject duplicate keys and non-finite constants."""
    content_type = response.headers.get("content-type", "")
    if content_type and "application/json" not in content_type.lower():
        raise ProtocolError("Comdirect API returned a non-JSON content type")
    try:
        return json.loads(
            response.body.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ProtocolError) as err:
        raise ProtocolError("Comdirect API returned malformed JSON") from err


def _path_token(value: str) -> str:
    if not isinstance(value, str):
        raise ProtocolError("API path identifier must be a string")
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 128 or any(ord(ch) < 33 or ord(ch) > 126 for ch in cleaned):
        raise ProtocolError("API path identifier is invalid")
    return cleaned


def _validate_header_value(value: str, field: str) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= 4096:
        raise ProtocolError(f"{field} is invalid")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ProtocolError(f"{field} contains control characters")


def _validate_opaque_token(value: str, field: str) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= 8192:
        raise ProtocolError(f"{field} is invalid")
    if any(ord(ch) < 33 or ord(ch) > 126 for ch in value):
        raise ProtocolError(f"{field} contains whitespace or control characters")


def _read_bounded(response: Any, maximum: int) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            declared = int(content_length)
        except ValueError as err:
            raise ProtocolError("Remote Content-Length is invalid") from err
        if declared < 0 or declared > maximum:
            raise ProtocolError("Remote response exceeds the size limit")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(65536, maximum - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > maximum:
            raise ProtocolError("Remote response exceeds the size limit")
        chunks.append(chunk)
    return b"".join(chunks)



def _read_error_body_bounded(response: Any, maximum: int) -> bytes:
    """Read a bounded error response without retaining it beyond classification."""
    try:
        return _read_bounded(response, maximum)
    except Exception:
        return b""


def _oauth_error_code(body: bytes, content_type: str | None) -> str | None:
    """Extract only a bounded OAuth error code; discard all other remote fields."""
    if not body or len(body) > 64 * 1024:
        return None
    if content_type and "json" not in content_type.lower():
        return None
    try:
        document = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ProtocolError):
        return None
    if not isinstance(document, dict):
        return None
    value = document.get("error")
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 64
        or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_" for char in value)
    ):
        return None
    return value

def _drain_bounded(response: Any, maximum: int) -> None:
    try:
        _read_bounded(response, maximum)
    except Exception:
        pass


def _bounded_headers(items: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    total = 0
    for key, value in items:
        key_lower = str(key).lower()
        value_string = str(value)
        total += len(key_lower) + len(value_string)
        if total > MAX_REMOTE_HEADER_BYTES:
            raise ProtocolError("Remote response headers exceed the safety limit")
        # Preserve only headers needed by the protocol. Never persist Set-Cookie.
        if key_lower in {
            "content-type",
            "retry-after",
            "x-once-authentication-info",
        }:
            result[key_lower] = value_string
    return result


def _parse_retry_after(value: str | None) -> int | None:
    if value is None or not value.isdecimal():
        return None
    seconds = int(value)
    return seconds if 0 <= seconds <= 3600 else None


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("Remote JSON contains a duplicate object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ProtocolError(f"Remote JSON constant {value} is not allowed")
