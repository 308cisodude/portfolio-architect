"""Admin-only multi-profile Generic Import UI and supported static provider runtime."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from email import policy
from email.parser import BytesHeaderParser
from html import escape
from http import HTTPStatus
from http.server import ThreadingHTTPServer
import json
import logging
from pathlib import Path
import re
import secrets
import threading
from typing import Any, Final
from urllib.parse import parse_qs, urlsplit

from . import __version__
from .acquisition_presentation import ACQUISITION_AUTHORITY_CSS, render_acquisition_authority
from .generic_csv import (
    CSV_DELIMITERS,
    CSV_ENCODINGS,
    DECIMAL_FORMATS,
    MAX_CSV_FILE_BYTES,
    GenericCsvConfig,
    GenericCsvImportError,
)
from .generic_profiles import (
    MAX_GENERIC_PROFILES,
    GenericProfile,
    GenericProfileManager,
    create_generic_multi_server,
)
from .pending_app import (
    APP_DATA_DIRECTORY,
    INGRESS_BIND,
    INGRESS_PORT,
    MAX_HEADER_BYTES,
    PendingAppOptions,
    ProviderShellIngressHandler,
    build_server_config,
)
from .runtime_config import ensure_api_token

_LOGGER = logging.getLogger(__name__)
MAX_MULTIPART_BYTES: Final = MAX_CSV_FILE_BYTES + 64 * 1024
MAX_BOUNDARY_BYTES: Final = 70
MAX_FORM_BYTES: Final = 8 * 1024
_PROFILE_ACTION_RE: Final = re.compile(
    r"^/profiles/([a-z][a-z0-9_]{1,31})/(rename|import|cash|clear-cash|delete)$"
)
_CASH_RE: Final = re.compile(r"^[0-9]{1,10}(?:[.,][0-9]{1,2})?$")
_TEXT_FIELDS: Final = frozenset(
    {
        "nonce",
        "encoding",
        "delimiter",
        "header_row",
        "decimal_format",
        "identifier_column",
        "name_column",
        "value_column",
        "isin_column",
        "type_column",
        "currency_column",
    }
)
_ALL_IMPORT_FIELDS: Final = _TEXT_FIELDS | {"csv"}


class GenericImportIngressServer(ThreadingHTTPServer):
    """Admin-only Ingress server for independent Generic provider profiles."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        manager: GenericProfileManager,
        api_token: str,
        allowed_sources: frozenset[str],
        require_user_header: bool,
    ) -> None:
        self.profile_manager = manager
        self.api_token = api_token
        self.allowed_sources = allowed_sources
        self.require_user_header = require_user_header
        self.form_nonce = secrets.token_urlsafe(32)
        super().__init__(address, GenericImportIngressHandler)


class GenericImportIngressHandler(ProviderShellIngressHandler):
    """Protected Generic Import profile, holdings, cash, and deletion workflow."""

    server_version = "PortfolioArchitectGenericImport"

    @property
    def import_server(self) -> GenericImportIngressServer:
        return self.server  # type: ignore[return-value]

    @property
    def shell_server(self) -> GenericImportIngressServer:  # type: ignore[override]
        return self.import_server

    def do_GET(self) -> None:  # noqa: N802
        if not self._authorised_ingress():
            self._empty(HTTPStatus.FORBIDDEN)
            return
        parsed = urlsplit(self.path)
        if parsed.path in {"", "/"}:
            query = parse_qs(parsed.query, keep_blank_values=False, strict_parsing=False)
            provider_id = _single_query_value(query, "profile")
            delete_id = _single_query_value(query, "delete")
            try:
                body = self._render_page(provider_id=provider_id, delete_id=delete_id)
            except GenericCsvImportError:
                self._html_status(self._render_page(), HTTPStatus.NOT_FOUND)
                return
            self._html_status(body, HTTPStatus.OK)
            return
        if parsed.path == "/health":
            self._json({"status": "ok", "profile_count": len(self.import_server.profile_manager.profiles())})
            return
        if parsed.path == "/status":
            self._json(self._status_document())
            return
        self._empty(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorised_ingress():
            self._empty(HTTPStatus.FORBIDDEN)
            return
        path = urlsplit(self.path).path
        try:
            if path == "/profiles/create":
                fields = self._read_urlencoded_form({"nonce", "provider_name"})
                self._require_nonce(fields.pop("nonce"))
                profile = self.import_server.profile_manager.create_profile(fields["provider_name"])
                _LOGGER.info("Generic Import source profile created")
                self._html_status(self._render_page(provider_id=profile.provider_id), HTTPStatus.OK)
                return

            match = _PROFILE_ACTION_RE.fullmatch(path)
            if match is None:
                self._empty(HTTPStatus.NOT_FOUND)
                return
            provider_id, action = match.groups()
            if self.import_server.profile_manager.runtime(provider_id) is None:
                raise GenericCsvImportError("Generic Import source profile does not exist")

            if action == "import":
                fields, document = self._read_import_form()
                self._require_nonce(fields.pop("nonce"))
                mapping = GenericCsvConfig.from_mapping(fields)
                summary = self.import_server.profile_manager.import_holdings(
                    provider_id,
                    document,
                    mapping,
                    generated_at=datetime.now(timezone.utc),
                )
                self.import_server.profile_manager.record_diagnostic(
                    provider_id,
                    "accepted",
                    f"CSV accepted: {summary.position_count} positions; holdings evidence timestamp "
                    f"{summary.generated_at.isoformat(timespec='seconds')}.",
                )
                _LOGGER.info("Generic mapped CSV import activated a validated profile snapshot")
            elif action == "rename":
                fields = self._read_urlencoded_form({"nonce", "provider_name"})
                self._require_nonce(fields.pop("nonce"))
                self.import_server.profile_manager.rename_profile(provider_id, fields["provider_name"])
                _LOGGER.info("Generic Import source profile label changed")
            elif action == "cash":
                fields = self._read_urlencoded_form({"nonce", "amount_eur"})
                self._require_nonce(fields.pop("nonce"))
                amount = _parse_cash_amount(fields["amount_eur"])
                stamp = self.import_server.profile_manager.set_cash(provider_id, amount)
                self.import_server.profile_manager.record_diagnostic(
                    provider_id,
                    "accepted",
                    f"Investment cash accepted; cash evidence timestamp {stamp.isoformat(timespec='seconds')}.",
                )
                _LOGGER.info("Generic Import investment cash evidence activated")
            elif action == "clear-cash":
                fields = self._read_urlencoded_form({"nonce", "confirm"})
                self._require_nonce(fields.pop("nonce"))
                if fields.get("confirm") != "yes":
                    raise GenericCsvImportError("Clearing investment cash requires explicit confirmation")
                self.import_server.profile_manager.clear_cash(provider_id)
                self.import_server.profile_manager.record_diagnostic(
                    provider_id,
                    "accepted",
                    "Investment cash cleared; holdings evidence was retained unchanged.",
                )
                _LOGGER.info("Generic Import investment cash evidence cleared")
            elif action == "delete":
                fields = self._read_urlencoded_form({"nonce", "provider_id", "confirm"})
                self._require_nonce(fields.pop("nonce"))
                if fields.get("provider_id") != provider_id or fields.get("confirm") != "yes":
                    raise GenericCsvImportError("Profile deletion requires explicit confirmation")
                self.import_server.profile_manager.delete_profile(provider_id)
                _LOGGER.info("Generic Import source profile and its private state deleted")
                self._html_status(self._render_page(), HTTPStatus.OK)
                return
            else:  # pragma: no cover - regex constrains this branch
                self._empty(HTTPStatus.NOT_FOUND)
                return

            self._html_status(self._render_page(provider_id=provider_id), HTTPStatus.OK)
        except GenericCsvImportError as err:
            _LOGGER.warning("Generic Import admin action rejected")
            if path.endswith("/import"):
                profile_id = _provider_id_from_action_path(path)
                if profile_id and self.import_server.profile_manager.runtime(profile_id) is not None:
                    self.import_server.profile_manager.record_diagnostic(
                        profile_id, "rejected", f"CSV rejected: {_public_import_error(err)}"
                    )
            selected = _provider_id_from_action_path(path)
            self._html_status(
                self._render_page(provider_id=selected, notice=_public_import_error(err), notice_bad=True),
                HTTPStatus.BAD_REQUEST,
            )
        except Exception:
            _LOGGER.exception("Generic Import admin action failed internally")
            selected = _provider_id_from_action_path(path)
            if selected and self.import_server.profile_manager.runtime(selected) is not None:
                try:
                    self.import_server.profile_manager.record_diagnostic(
                        selected,
                        "internal_error",
                        "Generic Import action failed internally; existing canonical evidence was retained where possible.",
                    )
                except Exception:
                    pass
            self._html_status(
                self._render_page(
                    provider_id=selected,
                    notice="The action failed internally; existing canonical evidence was retained where possible.",
                    notice_bad=True,
                ),
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    do_PUT = ProviderShellIngressHandler.do_POST
    do_PATCH = ProviderShellIngressHandler.do_POST
    do_DELETE = ProviderShellIngressHandler.do_POST
    do_HEAD = ProviderShellIngressHandler.do_POST
    do_OPTIONS = ProviderShellIngressHandler.do_POST

    def _require_nonce(self, value: str) -> None:
        if not secrets.compare_digest(value, self.import_server.form_nonce):
            raise GenericCsvImportError("Form session is invalid; reload the page and try again")

    def _read_urlencoded_form(self, allowed: set[str]) -> dict[str, str]:
        if sum(len(key) + len(value) for key, value in self.headers.items()) > MAX_HEADER_BYTES:
            raise GenericCsvImportError("Request headers are too large")
        if self.headers.get_content_type() != "application/x-www-form-urlencoded":
            raise GenericCsvImportError("Form request has an invalid content type")
        length = _bounded_content_length(self.headers.get("Content-Length"), MAX_FORM_BYTES)
        body = self.rfile.read(length)
        if len(body) != length:
            raise GenericCsvImportError("Form request body is incomplete")
        try:
            parsed = parse_qs(
                body.decode("utf-8"),
                keep_blank_values=True,
                strict_parsing=True,
                max_num_fields=12,
            )
        except (UnicodeDecodeError, ValueError) as err:
            raise GenericCsvImportError("Form request is invalid") from err
        if set(parsed) != allowed or any(len(values) != 1 for values in parsed.values()):
            raise GenericCsvImportError("Form request contains unexpected or duplicate fields")
        values = {key: items[0].strip() for key, items in parsed.items()}
        if any(len(value) > 512 for value in values.values()):
            raise GenericCsvImportError("Form field is too large")
        return values

    def _read_import_form(self) -> tuple[dict[str, str], bytes]:
        if sum(len(key) + len(value) for key, value in self.headers.items()) > MAX_HEADER_BYTES:
            raise GenericCsvImportError("Import request headers are too large")
        if self.headers.get_content_type() != "multipart/form-data":
            raise GenericCsvImportError("Import request must use multipart/form-data")
        boundary = self.headers.get_boundary()
        if not boundary:
            raise GenericCsvImportError("Import form boundary is missing")
        try:
            boundary_bytes = boundary.encode("ascii")
        except UnicodeEncodeError as err:
            raise GenericCsvImportError("Import form boundary is invalid") from err
        if not 1 <= len(boundary_bytes) <= MAX_BOUNDARY_BYTES or any(
            byte < 33 or byte > 126 for byte in boundary_bytes
        ):
            raise GenericCsvImportError("Import form boundary is invalid")
        length = _bounded_content_length(self.headers.get("Content-Length"), MAX_MULTIPART_BYTES)
        body = self.rfile.read(length)
        if len(body) != length:
            raise GenericCsvImportError("Import request body is incomplete")
        return _parse_multipart_body(body, boundary_bytes)

    def _status_document(self) -> dict[str, Any]:
        profiles: list[dict[str, Any]] = []
        for profile in self.import_server.profile_manager.profiles():
            runtime = self.import_server.profile_manager.runtime(profile.provider_id)
            snapshot = runtime.provider.snapshot if runtime is not None else None
            profiles.append(
                {
                    "provider_id": profile.provider_id,
                    "provider_name": profile.provider_name,
                    "ready": snapshot is not None,
                    "holdings_evidence_at": (
                        snapshot.generated_at.astimezone(timezone.utc).isoformat(timespec="seconds")
                        if snapshot is not None
                        else None
                    ),
                    "cash_evidence_at": (
                        snapshot.investment_cash.as_of.astimezone(timezone.utc).isoformat(timespec="seconds")
                        if snapshot is not None and snapshot.investment_cash is not None
                        else None
                    ),
                }
            )
        return {
            "schema_version": 1,
            "app_version": __version__,
            "profile_count": len(profiles),
            "ready_profile_count": sum(1 for item in profiles if item["ready"]),
            "profiles": profiles,
        }

    def _render_page(
        self,
        *,
        provider_id: str | None = None,
        delete_id: str | None = None,
        notice: str | None = None,
        notice_bad: bool = False,
    ) -> bytes:
        manager = self.import_server.profile_manager
        profiles = manager.profiles()
        selected: GenericProfile | None = None
        if provider_id:
            selected = next((item for item in profiles if item.provider_id == provider_id), None)
            if selected is None:
                raise GenericCsvImportError("Generic Import source profile does not exist")
        delete_profile: GenericProfile | None = None
        if delete_id:
            delete_profile = next((item for item in profiles if item.provider_id == delete_id), None)
            if delete_profile is None:
                raise GenericCsvImportError("Generic Import source profile does not exist")

        notice_html = ""
        if notice:
            css = "bad" if notice_bad else "good"
            notice_html = f'<section class="notice {css}"><strong>{escape(notice)}</strong></section>'

        profile_cards = "".join(self._profile_card(item) for item in profiles)
        if not profile_cards:
            profile_cards = (
                '<p class="warn"><strong>Setup required.</strong> Create a source profile for the bank or broker '
                "whose CSV export you want Portfolio Architect to consume.</p>"
            )

        details_html = self._profile_details(selected) if selected else ""
        delete_html = self._delete_confirmation(delete_profile) if delete_profile else ""
        create_disabled = " disabled" if len(profiles) >= MAX_GENERIC_PROFILES else ""
        nonce = escape(self.import_server.form_nonce)
        body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfolio Architect Gateway — Generic Import</title>
<style>
:root{{color-scheme:dark}}body{{font-family:system-ui,sans-serif;max-width:1040px;margin:2rem auto;padding:0 1rem;background:#111;color:#eee}}section{{border:1px solid #444;border-radius:12px;padding:1rem;margin:1rem 0}}a{{color:#77c9ff}}code{{word-break:break-all}}label{{display:block;margin:.7rem 0 .2rem}}input,select{{box-sizing:border-box;width:100%;max-width:680px;padding:.55rem;background:#1b1b1b;color:#eee;border:1px solid #555;border-radius:6px}}button,.button{{display:inline-block;margin-top:1rem;padding:.65rem 1rem;border-radius:7px;border:1px solid #6b9db7;background:#173b4d;color:#fff;font-weight:600;text-decoration:none}}button.danger,.button.danger{{border-color:#b85b5b;background:#4b1f1f}}button:disabled{{opacity:.45}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.75rem}}.profile-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:.75rem}}.profile-card{{border:1px solid #555;border-radius:10px;padding:.9rem}}.good{{color:#7bd88f}}.warn{{color:#ffca28}}.bad{{color:#ff7b7b}}small,.muted{{color:#bbb}}.notice{{border-width:2px}}.actions{{display:flex;gap:.7rem;flex-wrap:wrap;align-items:center}}.actions form{{margin:0}}.inline-check{{display:flex;gap:.5rem;align-items:center}}.inline-check input{{width:auto}}{ACQUISITION_AUTHORITY_CSS}
</style></head><body><main>
<h1>Portfolio Architect Gateway — Generic Import</h1>
<p class="muted">Supported provider-neutral static acquisition for banks and brokers without a dedicated Portfolio Architect Gateway. One App may host multiple independent source profiles; each keeps its own immutable provider identity, holdings, investment cash and evidence clocks.</p>
{notice_html}
<section><h2>Source profiles</h2><p>Raw CSV bytes are parsed transiently and are never persisted. A source is advertised to Portfolio Architect only after its first validated holdings import.</p><div class="profile-grid">{profile_cards}</div></section>
<section><h2>Add source profile</h2><form method="post" action="profiles/create"><input type="hidden" name="nonce" value="{nonce}"><label for="provider_name">Bank or broker name</label><input id="provider_name" name="provider_name" maxlength="64" placeholder="Example Bank" required{create_disabled}><button type="submit"{create_disabled}>Create source</button></form><p><small>Up to {MAX_GENERIC_PROFILES} Generic profiles can coexist. The human name can be changed later; the generated machine provider ID never changes.</small></p></section>
{delete_html}{details_html}
<section><h2>Connection boundary</h2><p>Portfolio Architect consumes each ready profile as an ordinary read-only provider over one shared verified private-PKI HTTPS App boundary. Provider identity is verified end-to-end; one profile cannot silently substitute for another.</p><p>This App has no live-provider credentials and no order, transfer, payment, transaction-history, sell or withdrawal capability.</p></section>
<section><h2>Sensitive connection material</h2><p><small>The App-private bearer token is needed only when explicitly adopting a discovered Generic source in Portfolio Architect. It is deliberately kept away from the screenshot-prone top of this page.</small></p><details><summary>Show bearer token</summary><p>Bearer token: <code>{escape(self.import_server.api_token)}</code></p></details></section>
</main></body></html>"""
        return body.encode("utf-8")

    def _profile_card(self, profile: GenericProfile) -> str:
        runtime = self.import_server.profile_manager.runtime(profile.provider_id)
        snapshot = runtime.provider.snapshot if runtime is not None else None
        ready = snapshot is not None
        status = '<span class="good">READY</span>' if ready else '<span class="warn">SETUP REQUIRED</span>'
        holdings = (
            escape(snapshot.generated_at.astimezone(timezone.utc).isoformat(timespec="seconds"))
            if snapshot is not None
            else "not imported"
        )
        cash = (
            escape(snapshot.investment_cash.as_of.astimezone(timezone.utc).isoformat(timespec="seconds"))
            if snapshot is not None and snapshot.investment_cash is not None
            else "not recorded"
        )
        return (
            f'<article class="profile-card"><h3>{escape(profile.provider_name)}</h3><p>{status}</p>'
            f'<p>Provider ID: <code>{escape(profile.provider_id)}</code></p>'
            f'<p><small>Holdings evidence: {holdings}<br>Cash evidence: {cash}</small></p>'
            f'<a class="button" href="?profile={escape(profile.provider_id)}">Manage source</a> '
            f'<a class="button danger" href="?profile={escape(profile.provider_id)}&delete={escape(profile.provider_id)}">Delete…</a></article>'
        )

    def _profile_details(self, profile: GenericProfile) -> str:
        manager = self.import_server.profile_manager
        runtime = manager.runtime(profile.provider_id)
        if runtime is None:
            raise GenericCsvImportError("Generic Import source runtime is unavailable")
        snapshot = runtime.provider.snapshot
        health = runtime.state.health_document(version=10)
        try:
            mapping = manager.load_mapping(profile.provider_id)
            mapping_error = ""
        except GenericCsvImportError:
            mapping = GenericCsvConfig()
            mapping_error = '<p class="bad">Stored mapping is invalid; defaults are shown.</p>'
        diagnostic = manager.diagnostic(profile.provider_id)
        diagnostic_html = "<p>No import diagnostic recorded yet.</p>"
        if diagnostic is not None:
            diagnostic_html = (
                f"<p><strong>{escape(diagnostic['outcome'])}</strong> · {escape(diagnostic['recorded_at'])}</p>"
                f"<p>{escape(diagnostic['message'])}</p>"
            )
        authority_html = render_acquisition_authority(
            runtime.provider.acquisition_control,
            evidence_timestamps=runtime.state.capability_evidence_timestamps(),
        )
        snapshot_text = (
            f"{len(snapshot.positions)} positions · {escape(snapshot.generated_at.astimezone(timezone.utc).isoformat(timespec='seconds'))}"
            if snapshot is not None
            else "No holdings CSV imported yet"
        )
        cash_text = (
            f"EUR {escape(format(snapshot.investment_cash.authorized_eur, 'f'))} · {escape(snapshot.investment_cash.as_of.astimezone(timezone.utc).isoformat(timespec='seconds'))}"
            if snapshot is not None and snapshot.investment_cash is not None
            else "No provider-local investment cash recorded"
        )
        status = escape(str(health.get("status", "degraded")))
        status_class = "good" if status == "ok" else "warn"
        nonce = escape(self.import_server.form_nonce)
        provider_id = escape(profile.provider_id)
        return f"""
<section><h2>Manage source · {escape(profile.provider_name)}</h2>
<p>Immutable provider ID: <code>{provider_id}</code></p><p>Gateway status: <strong class="{status_class}">{status}</strong></p>
<p>Holdings: <strong>{snapshot_text}</strong><br>Investment cash: <strong>{cash_text}</strong></p>
<form method="post" action="profiles/{provider_id}/rename"><input type="hidden" name="nonce" value="{nonce}"><label for="rename_{provider_id}">Display name</label><input id="rename_{provider_id}" name="provider_name" maxlength="64" value="{escape(profile.provider_name)}" required><button type="submit">Rename source</button></form>
</section>
{authority_html}
<section><h2>Import holdings CSV</h2>{mapping_error}
<form method="post" action="profiles/{provider_id}/import" enctype="multipart/form-data"><input type="hidden" name="nonce" value="{nonce}">
<label for="csv_{provider_id}">CSV file</label><input id="csv_{provider_id}" name="csv" type="file" accept=".csv,text/csv,text/plain" required>
<div class="grid"><div><label>Encoding</label><select name="encoding">{_options(CSV_ENCODINGS, mapping.encoding)}</select></div><div><label>Delimiter</label><select name="delimiter">{_options(CSV_DELIMITERS, mapping.delimiter)}</select></div><div><label>Header row</label><input name="header_row" type="number" min="1" max="50" value="{mapping.header_row}" required></div><div><label>Number format</label><select name="decimal_format">{_options(DECIMAL_FORMATS, mapping.decimal_format)}</select></div></div>
<div class="grid"><div><label>Identifier column</label><input name="identifier_column" value="{escape(mapping.identifier_column)}" maxlength="160" required></div><div><label>Name column</label><input name="name_column" value="{escape(mapping.name_column)}" maxlength="160" required></div><div><label>EUR market-value column</label><input name="value_column" value="{escape(mapping.value_column)}" maxlength="160" required></div><div><label>ISIN column (optional)</label><input name="isin_column" value="{escape(mapping.isin_column or '')}" maxlength="160"></div><div><label>Instrument-type column (optional)</label><input name="type_column" value="{escape(mapping.type_column or '')}" maxlength="160"></div><div><label>Currency column (optional)</label><input name="currency_column" value="{escape(mapping.currency_column or '')}" maxlength="160"></div></div>
<p><small>If Currency is mapped, every imported position must explicitly contain EUR or €. No conversion occurs. A successful import atomically replaces this profile's canonical holdings while retaining independently recorded cash. Rejected imports leave the previous canonical snapshot intact.</small></p><button type="submit">Validate and activate holdings</button></form></section>
<section><h2>Provider-local investment cash</h2><p>Optional. Enter the EUR amount that may be treated as fully available investment cash at this institution. Submission time becomes the independent cash evidence timestamp.</p>
<form method="post" action="profiles/{provider_id}/cash"><input type="hidden" name="nonce" value="{nonce}"><label>Available investment cash (EUR)</label><input name="amount_eur" inputmode="decimal" placeholder="0.00" required><button type="submit">Record investment cash</button></form>
<form method="post" action="profiles/{provider_id}/clear-cash" class="actions"><input type="hidden" name="nonce" value="{nonce}"><input type="hidden" name="confirm" value="yes"><button class="danger" type="submit">Clear recorded cash</button></form><p><small>Clearing cash does not alter holdings or their evidence timestamp.</small></p></section>
<section><h2>Last profile action</h2>{diagnostic_html}</section>"""

    def _delete_confirmation(self, profile: GenericProfile) -> str:
        nonce = escape(self.import_server.form_nonce)
        provider_id = escape(profile.provider_id)
        return f"""<section class="notice bad"><h2>Confirm source-profile deletion</h2><p><strong>Deleting: {escape(profile.provider_name)} · <code>{provider_id}</code></strong></p><p>This permanently removes this profile's normalized holdings, cash, mapping and bounded diagnostics from the Generic Import App. Raw CSV files were never persisted.</p><p><strong>Remove this provider from Portfolio Architect first if it is currently configured there.</strong> This App deliberately has no Home Assistant API permission and therefore cannot inspect or mutate Portfolio Architect configuration for you.</p><form method="post" action="profiles/{provider_id}/delete"><input type="hidden" name="nonce" value="{nonce}"><input type="hidden" name="provider_id" value="{provider_id}"><label class="inline-check"><input type="checkbox" name="confirm" value="yes" required> Confirm permanent profile deletion</label><button class="danger" type="submit">Delete source profile</button></form></section>"""

    def _html_status(self, body: bytes, status: HTTPStatus) -> None:
        self.send_response(status)
        self._security_headers("text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _single_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if values is None:
        return None
    if len(values) != 1 or len(values[0]) > 64:
        raise GenericCsvImportError("Query parameter is invalid")
    return values[0]


def _provider_id_from_action_path(path: str) -> str | None:
    match = _PROFILE_ACTION_RE.fullmatch(path)
    return match.group(1) if match is not None else None


def _bounded_content_length(value: str | None, maximum: int) -> int:
    try:
        length = int(value or "")
    except ValueError as err:
        raise GenericCsvImportError("Request content length is invalid") from err
    if not 1 <= length <= maximum:
        raise GenericCsvImportError("Request body is empty or exceeds the allowed size")
    return length


def _parse_cash_amount(value: str) -> Decimal:
    token = str(value or "").strip()
    if _CASH_RE.fullmatch(token) is None:
        raise GenericCsvImportError("Investment cash must be a non-negative EUR amount with at most two decimals")
    try:
        return Decimal(token.replace(",", "."))
    except InvalidOperation as err:  # pragma: no cover - regex already constrains the token
        raise GenericCsvImportError("Investment cash amount is invalid") from err


def _options(values: tuple[str, ...], selected: str) -> str:
    return "".join(
        f'<option value="{escape(value)}"{" selected" if value == selected else ""}>{escape(value)}</option>'
        for value in values
    )


def _parse_multipart_body(body: bytes, boundary: bytes) -> tuple[dict[str, str], bytes]:
    delimiter = b"--" + boundary
    closing = delimiter + b"--"
    if not body.startswith(delimiter + b"\r\n") or closing not in body:
        raise GenericCsvImportError("Import form body is malformed")
    fields: dict[str, bytes] = {}
    for raw_part in body.split(delimiter)[1:]:
        if raw_part.startswith(b"--"):
            break
        if not raw_part.startswith(b"\r\n"):
            raise GenericCsvImportError("Import form part is malformed")
        part = raw_part[2:]
        if part.endswith(b"\r\n"):
            part = part[:-2]
        try:
            header_blob, payload = part.split(b"\r\n\r\n", 1)
        except ValueError as err:
            raise GenericCsvImportError("Import form part headers are malformed") from err
        if len(header_blob) > 8192:
            raise GenericCsvImportError("Import form part headers are too large")
        headers = BytesHeaderParser(policy=policy.default).parsebytes(header_blob + b"\r\n")
        if headers.get_content_disposition() != "form-data":
            raise GenericCsvImportError("Import form part disposition is invalid")
        field = headers.get_param("name", header="content-disposition")
        if field not in _ALL_IMPORT_FIELDS or field in fields:
            raise GenericCsvImportError("Import form contains unexpected or duplicate fields")
        if field == "csv":
            if headers.get_content_type() not in {
                "text/csv",
                "text/plain",
                "application/csv",
                "application/vnd.ms-excel",
                "application/octet-stream",
            }:
                raise GenericCsvImportError("Uploaded document must be a CSV file")
            if not payload or len(payload) > MAX_CSV_FILE_BYTES:
                raise GenericCsvImportError("CSV is empty or exceeds the 10 MiB import limit")
        elif len(payload) > 512:
            raise GenericCsvImportError("Import form field is too large")
        fields[str(field)] = payload
    if set(fields) != _ALL_IMPORT_FIELDS:
        raise GenericCsvImportError("Import form is incomplete")
    text: dict[str, str] = {}
    for field in _TEXT_FIELDS:
        try:
            text[field] = fields[field].decode("utf-8").strip()
        except UnicodeDecodeError as err:
            raise GenericCsvImportError("Import form text field is invalid") from err
    return text, fields["csv"]


def _public_import_error(err: GenericCsvImportError) -> str:
    message = str(err).strip()
    if not message or len(message) > 240 or any(ord(char) < 32 for char in message):
        return "The Generic Import action could not be validated safely."
    return message


def serve_generic_import_app(
    *,
    provider_name: str,
    options: PendingAppOptions | None = None,
    data_directory: Path = APP_DATA_DIRECTORY,
    ingress_address: tuple[str, int] = (INGRESS_BIND, INGRESS_PORT),
    allowed_ingress_sources: frozenset[str] = frozenset({"172.30.32.2"}),
    require_user_header: bool = True,
    discovery_changed: Callable[[tuple[GenericProfile, ...]], None] | None = None,
    tls_cert_file: Path | None = None,
    tls_key_file: Path | None = None,
) -> None:
    """Run the supported multi-profile Generic Import Gateway."""
    del provider_name  # App package name is no longer a provider identity.
    data_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if options is None:
        options = PendingAppOptions.load()
    server_config = build_server_config(
        options,
        data_directory,
        tls_cert_file=tls_cert_file,
        tls_key_file=tls_key_file,
    )
    api_token = ensure_api_token(server_config.api_token_file)
    manager = GenericProfileManager(
        data_directory,
        server_config,
        discovery_changed=discovery_changed,
    )
    gateway_server = create_generic_multi_server(server_config, manager)
    ingress_server = GenericImportIngressServer(
        ingress_address,
        manager=manager,
        api_token=api_token,
        allowed_sources=allowed_ingress_sources,
        require_user_header=require_user_header,
    )
    gateway_thread = threading.Thread(
        target=gateway_server.serve_forever,
        kwargs={"poll_interval": 0.5},
        name="portfolio-generic-import-api",
        daemon=True,
    )
    gateway_thread.start()
    _LOGGER.info("Generic Import multi-profile Gateway initialized")
    if discovery_changed is not None:
        discovery_changed(manager.ready_profiles())
    try:
        ingress_server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        _LOGGER.info("Generic Import Gateway shutdown requested")
    finally:
        ingress_server.shutdown()
        ingress_server.server_close()
        gateway_server.shutdown()
        gateway_server.server_close()
        gateway_thread.join(timeout=5)
