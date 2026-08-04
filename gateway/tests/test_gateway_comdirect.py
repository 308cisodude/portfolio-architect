from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json

import pytest

from portfolio_architect_gateway.comdirect import ComdirectClient, TokenState
from portfolio_architect_gateway.config import ComdirectConfig
from portfolio_architect_gateway.errors import ProtocolError
from portfolio_architect_gateway.transport import HttpResponse


def response(value, *, headers=None):
    return HttpResponse(
        status=200,
        body=json.dumps(value, separators=(",", ":")).encode(),
        headers={"content-type": "application/json", **(headers or {})},
    )


class FakeTransport:
    def __init__(self) -> None:
        self.qsession = "qsession-value"
        self.activated = False
        self.refresh_called = False

    def restore_qsession(self, value):
        if value:
            self.qsession = value

    def current_qsession(self):
        return self.qsession

    def oauth_password(self, **kwargs):
        assert kwargs["username"] == "user"
        return response(
            {
                "access_token": "initial-token",
                "expires_in": 300,
                "token_type": "Bearer",
                "scope": "SESSION_RW",
            }
        )

    def get_sessions(self, *, bearer):
        assert bearer == "initial-token"
        return response(
            [
                {
                    "identifier": "session-1",
                    "sessionTanActive": False,
                    "activated2FA": False,
                }
            ]
        )

    def validate_session(self, **kwargs):
        assert kwargs["session_id"] == "session-1"
        return response(
            {},
            headers={
                "x-once-authentication-info": json.dumps(
                    {"id": "challenge-1", "typ": "P_TAN_PUSH"}
                )
            },
        )

    def activate_session(self, **kwargs):
        assert kwargs["session_document"]["sessionTanActive"] is True
        assert kwargs["session_document"]["activated2FA"] is True
        assert kwargs["once_authentication_info"] == '{"id":"challenge-1"}'
        assert kwargs["once_authentication"] is None
        self.activated = True
        return response({})

    def oauth_secondary(self, **kwargs):
        assert self.activated
        return response(
            {
                "access_token": "secondary-token",
                "refresh_token": "refresh-token",
                "expires_in": 900,
                "token_type": "Bearer",
                "scope": "BROKERAGE_RW",
            }
        )

    def oauth_refresh(self, **kwargs):
        self.refresh_called = True
        return response(
            {
                "access_token": "refreshed-token",
                "expires_in": 900,
                "token_type": "Bearer",
                "scope": "BROKERAGE_RW",
            }
        )

    def poll_session_challenge(self, **kwargs):
        raise AssertionError("no challenge link was supplied")

    def get_account_balances(self, *, bearer):
        assert bearer in {"secondary-token", "refreshed-token"}
        return response(
            {
                "values": [
                    {
                        "account": {
                            "accountId": "ACCOUNT-1",
                            "accountDisplayId": "DE00123456789012345678",
                            "accountType": "Girokonto",
                            "currency": "EUR",
                        },
                        "balanceEUR": {"value": "1050.00", "unit": "EUR"},
                        "availableCashAmountEUR": {"value": "1050.00", "unit": "EUR"},
                    },
                    {
                        "account": {
                            "accountId": "CARD-1",
                            "accountDisplayId": "9999",
                            "accountType": "CREDIT_CARD",
                            "currency": "EUR",
                        },
                        "balanceEUR": {"value": "5000.00", "unit": "EUR"},
                        "availableCashAmountEUR": {"value": "5000.00", "unit": "EUR"},
                    },
                ]
            }
        )

    def get_depots(self, *, bearer):
        assert bearer in {"secondary-token", "refreshed-token"}
        return response({"values": [{"depotId": "D1"}, {"depotId": "D2"}]})

    def get_positions(self, *, depot_id, first, count, bearer):
        if first:
            return response({"values": [], "paging": {"matches": 1}})
        amount = "100.25" if depot_id == "D1" else "50.75"
        return response(
            {
                "values": [
                    {
                        "wkn": "A1XB5U",
                        "instrumentId": "instrument-1",
                        "currentValue": {"value": amount, "unit": "EUR"},
                    }
                ],
                "paging": {"matches": 1},
            }
        )


    def get_instrument_probe(self, *, isin, bearer):
        assert isin == "IE00BJ0KDQ92"
        return response({
            "isin": isin,
            "wkn": "A1XB5U",
            "name": "ETF One",
            "fundsDistribution": {
                "fundStatus": "A",
                "fundFlags": ["FLAG_B", "FLAG_A"],
                "currency": "EUR",
                "regularIssueSurcharge": "1.500",
            },
            "orderDimensions": {
                "venues": [
                    {
                        "name": "Tradegate",
                        "venueId": "VENUE-PRIVATE-1",
                        "country": "DE",
                        "type": "EXCHANGE",
                        "currencies": ["EUR"],
                        "sides": ["BUY", "SELL"],
                        "orderTypes": {"MARKET": {}},
                    },
                    {
                        "name": "Sell only",
                        "venueId": "VENUE-PRIVATE-2",
                        "country": "DE",
                        "type": "EXCHANGE",
                        "currencies": ["EUR"],
                        "sides": ["SELL"],
                        "orderTypes": {"MARKET": {}},
                    },
                ]
            },
        })

    def post_cost_indication(self, *, order_document, bearer):
        assert order_document == {
            "depotId": "D1",
            "side": "BUY",
            "instrumentId": "IE00BJ0KDQ92",
            "venueId": "VENUE-PRIVATE-1",
            "quantity": {"value": "1", "unit": "XXX"},
            "orderType": "MARKET",
            "validityType": "GFD",
            "bestEx": False,
        }
        return response({"values": [{
            "depotId": "D1",
            "calculationSuccessful": True,
            "name": "ETF One",
            "wkn": "A1XB5U",
            "side": "BUY",
            "quantity": {"value": "1", "unit": "XXX"},
            "expectedValue": {"value": "105.00", "unit": "EUR"},
            "venueName": "Tradegate",
            "settlementCurrency": "EUR",
            "tradingCurrency": "EUR",
            "reportingCurrency": "EUR",
            "expectedSettlementCosts": {"value": "9.90", "unit": "EUR"},
            "purchaseCosts": {
                "type": "K",
                "label": "Kaufkosten",
                "sum": {"value": "9.90", "unit": "EUR"},
                "costs": [{
                    "type": "E",
                    "label": "Orderprovision",
                    "amount": {"value": "9.90", "unit": "EUR"},
                    "amountReportingCurrency": {"value": "9.90", "unit": "EUR"},
                    "inducement": {"secret": "not-retained"},
                }],
            },
            "holdingCosts": {"type": "H", "label": "Halten", "sum": {"value": "1.20", "unit": "EUR"}, "costs": []},
            "salesCosts": {"type": "V", "label": "Verkauf", "sum": {"value": "9.90", "unit": "EUR"}, "costs": []},
            "holdingPeriod": "5",
            "totalCostsAbs": {"value": "25.80", "unit": "EUR"},
            "totalCostsRel": {"percentString": "24.57"},
            "linkCosts": "https://example.invalid/private",
        }]})

    def get_instrument(self, *, instrument_id, bearer):
        assert instrument_id == "instrument-1"
        return response(
            {
                "instrumentId": instrument_id,
                "wkn": "A1XB5U",
                "isin": "IE00BJ0KDQ92",
                "name": "ETF One",
                "staticData": {"instrumentType": {"text": "ETF"}},
            }
        )


def config(tmp_path: Path) -> ComdirectConfig:
    values = {
        "client_id": "client",
        "client_secret": "secret",
        "username": "user",
        "password": "password",
    }
    paths = {}
    for name, value in values.items():
        path = tmp_path / name
        path.write_text(value)
        path.chmod(0o600)
        paths[name] = path
    return ComdirectConfig(
        base_url="https://api.comdirect.de",
        client_id_file=paths["client_id"],
        client_secret_file=paths["client_secret"],
        username_file=paths["username"],
        password_file=paths["password"],
        session_file=tmp_path / "session.json",
        investment_account_file=tmp_path / "investment-account.json",
        poll_interval_seconds=900,
        request_timeout_seconds=20,
        mfa_timeout_seconds=180,
        depot_ids=(),
    )


def test_interactive_bootstrap_persists_only_session_material(tmp_path: Path) -> None:
    transport = FakeTransport()
    client = ComdirectClient(config(tmp_path), transport=transport, clock=lambda: 1000)
    state = client.bootstrap(prompt=lambda _message: "", output=lambda _message: None)
    assert state.access_token == "secondary-token"
    persisted = json.loads((tmp_path / "session.json").read_text())
    assert persisted["refresh_token"] == "refresh-token"
    assert "username" not in persisted
    assert "password" not in persisted
    assert (tmp_path / "session.json").stat().st_mode & 0o777 == 0o600


def test_portfolio_fetch_aggregates_same_wkn_across_depots(tmp_path: Path) -> None:
    transport = FakeTransport()
    client = ComdirectClient(config(tmp_path), transport=transport, clock=lambda: 1000)
    client.bootstrap(prompt=lambda _message: "", output=lambda _message: None)
    snapshot = client.fetch_snapshot()
    assert snapshot.positions[0].identifier == "A1XB5U"
    assert str(snapshot.positions[0].market_value_eur) == "151.00"
    assert snapshot.positions[0].isin == "IE00BJ0KDQ92"
    assert snapshot.positions[0].instrument_type == "ETF"



def test_investment_account_selection_is_masked_and_added_to_snapshot(tmp_path: Path) -> None:
    transport = FakeTransport()
    client = ComdirectClient(config(tmp_path), transport=transport, clock=lambda: 1000)
    client.bootstrap(prompt=lambda _message: "", output=lambda _message: None)
    candidates = client.discover_investment_accounts()
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.account_id == "ACCOUNT-1"
    assert candidate.masked_label == "Girokonto · …5678"
    assert candidate.available_eur == pytest.approx(Decimal("1050.00"))

    selected = client.select_investment_account(candidate.account_id)
    assert selected.account_id == candidate.account_id
    assert selected.masked_label == candidate.masked_label
    assert selected.available_eur == candidate.available_eur
    stored = json.loads((tmp_path / "investment-account.json").read_text())
    assert stored == {"schema_version": 1, "account_id": "ACCOUNT-1"}
    assert (tmp_path / "investment-account.json").stat().st_mode & 0o777 == 0o600

    snapshot = client.fetch_snapshot()
    assert snapshot.investment_reserve_eur == Decimal("1050.00")
    assert snapshot.investment_reserve_as_of is not None
    document = snapshot.as_dict()
    assert document["investment_reserve"]["available_eur"] == "1050"
    assert "ACCOUNT-1" not in json.dumps(document)
    assert "5678" not in json.dumps(document)

    client.clear_investment_account()
    assert client.selected_investment_account_id() is None
    assert client.fetch_snapshot().investment_reserve_eur is None


def test_investment_reserve_excludes_credit_line_and_pending_cash(tmp_path: Path) -> None:
    class BuyingPowerTransport(FakeTransport):
        def get_account_balances(self, *, bearer):
            return response(
                {
                    "values": [
                        {
                            "account": {
                                "accountId": "ACCOUNT-1",
                                "accountDisplayId": "DE00123456789012345678",
                                "accountType": "Girokonto",
                                "currency": "EUR",
                            },
                            "balanceEUR": {"value": "1000.00", "unit": "EUR"},
                            "availableCashAmountEUR": {
                                "value": "2000.00",
                                "unit": "EUR",
                            },
                        },
                        {
                            "account": {
                                "accountId": "ACCOUNT-2",
                                "accountDisplayId": "DE00999999999999999999",
                                "accountType": "Verrechnungskonto",
                                "currency": "EUR",
                            },
                            "balanceEUR": {"value": "1200.00", "unit": "EUR"},
                            "availableCashAmountEUR": {
                                "value": "900.00",
                                "unit": "EUR",
                            },
                        },
                    ]
                }
            )

    client = ComdirectClient(
        config(tmp_path), transport=BuyingPowerTransport(), clock=lambda: 1000
    )
    client.bootstrap(prompt=lambda _message: "", output=lambda _message: None)
    candidates = {item.account_id: item for item in client.discover_investment_accounts()}
    assert candidates["ACCOUNT-1"].available_eur == Decimal("1000.00")
    assert candidates["ACCOUNT-2"].available_eur == Decimal("900.00")


def test_investment_account_without_balance_and_available_cash_is_not_eligible(
    tmp_path: Path,
) -> None:
    class IncompleteBalanceTransport(FakeTransport):
        def get_account_balances(self, *, bearer):
            return response(
                {
                    "values": [
                        {
                            "account": {
                                "accountId": "ACCOUNT-1",
                                "accountDisplayId": "DE00123456789012345678",
                                "accountType": "Girokonto",
                                "currency": "EUR",
                            },
                            "availableCashAmountEUR": {
                                "value": "1050.00",
                                "unit": "EUR",
                            },
                        }
                    ]
                }
            )

    client = ComdirectClient(
        config(tmp_path), transport=IncompleteBalanceTransport(), clock=lambda: 1000
    )
    client.bootstrap(prompt=lambda _message: "", output=lambda _message: None)
    assert client.discover_investment_accounts() == ()


def test_selected_investment_account_missing_from_live_response_fails_closed(tmp_path: Path) -> None:
    transport = FakeTransport()
    client = ComdirectClient(config(tmp_path), transport=transport, clock=lambda: 1000)
    client.bootstrap(prompt=lambda _message: "", output=lambda _message: None)
    client.select_investment_account("ACCOUNT-1")

    class MissingAccount(FakeTransport):
        def get_account_balances(self, *, bearer):
            return response({"values": []})

    other = tmp_path / "other"
    other.mkdir()
    cfg = config(other)
    # Preserve the validated private selection and OAuth session in the replacement client.
    cfg.investment_account_file.parent.mkdir(parents=True, exist_ok=True)
    cfg.investment_account_file.write_text(
        json.dumps({"schema_version": 1, "account_id": "ACCOUNT-1"})
    )
    cfg.investment_account_file.chmod(0o600)
    state = TokenState(
        access_token="secondary-token",
        refresh_token="refresh-token",
        expires_at=5000,
        scope="BROKERAGE_RW",
        qsession="qsession-value",
    )
    cfg.session_file.write_text(json.dumps(state.as_dict()))
    cfg.session_file.chmod(0o600)
    missing = ComdirectClient(cfg, transport=MissingAccount(), clock=lambda: 1000)
    with pytest.raises(ProtocolError, match="not present"):
        missing.fetch_snapshot()

def test_expired_session_uses_refresh_token_without_password_flow(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    state = TokenState(
        access_token="expired",
        refresh_token="refresh-token",
        expires_at=1,
        scope="BROKERAGE_RW",
        qsession="qsession-value",
    )
    (tmp_path / "session.json").write_text(json.dumps(state.as_dict()))
    (tmp_path / "session.json").chmod(0o600)
    transport = FakeTransport()
    client = ComdirectClient(cfg, transport=transport, clock=lambda: 1000)
    assert client.ensure_access_token() == "refreshed-token"
    assert transport.refresh_called


def test_non_eur_bank_position_fails_closed(tmp_path: Path) -> None:
    class BadCurrency(FakeTransport):
        def get_positions(self, *, depot_id, first, count, bearer):
            return response(
                {
                    "values": [
                        {
                            "wkn": "A1XB5U",
                            "instrumentId": "instrument-1",
                            "currentValue": {"value": "100", "unit": "USD"},
                        }
                    ],
                    "paging": {"matches": 1},
                }
            )

    client = ComdirectClient(config(tmp_path), transport=BadCurrency(), clock=lambda: 1000)
    client.bootstrap(prompt=lambda _message: "", output=lambda _message: None)
    with pytest.raises(ProtocolError, match="EUR"):
        client.fetch_snapshot()


def test_in_memory_bootstrap_does_not_require_username_or_password_files(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    cfg.username_file.unlink()
    cfg.password_file.unlink()
    transport = FakeTransport()
    client = ComdirectClient(cfg, transport=transport, clock=lambda: 1000)
    state = client.bootstrap_with_credentials(
        client_id="client",
        client_secret="secret",
        username="user",
        password="password",
        prompt=lambda _message: "",
        output=lambda _message: None,
    )
    assert state.refresh_token == "refresh-token"
    persisted = (tmp_path / "session.json").read_text()
    assert "user" not in persisted
    assert "password" not in persisted


def _expired_client(tmp_path: Path, transport: FakeTransport) -> ComdirectClient:
    cfg = config(tmp_path)
    state = TokenState(
        access_token="expired",
        refresh_token="refresh-token",
        expires_at=1,
        scope="BROKERAGE_RW",
        qsession="qsession-value",
    )
    cfg.session_file.write_text(json.dumps(state.as_dict()))
    cfg.session_file.chmod(0o600)
    return ComdirectClient(cfg, transport=transport, clock=lambda: 1000)


def test_transient_refresh_failure_is_not_misclassified_as_reauthentication(tmp_path: Path) -> None:
    from portfolio_architect_gateway.errors import RemoteApiError

    class TransientRefresh(FakeTransport):
        def oauth_refresh(self, **kwargs):
            raise RemoteApiError(
                503,
                "Comdirect API returned HTTP 503",
                operation="oauth_refresh",
            )

    with pytest.raises(RemoteApiError) as raised:
        _expired_client(tmp_path, TransientRefresh()).ensure_access_token()
    assert raised.value.status == 503


def test_invalid_grant_requires_interactive_reauthentication(tmp_path: Path) -> None:
    from portfolio_architect_gateway.errors import ReauthenticationRequired, RemoteApiError

    class InvalidGrant(FakeTransport):
        def oauth_refresh(self, **kwargs):
            raise RemoteApiError(
                400,
                "Comdirect API returned HTTP 400",
                operation="oauth_refresh",
                error_code="invalid_grant",
            )

    with pytest.raises(ReauthenticationRequired):
        _expired_client(tmp_path, InvalidGrant()).ensure_access_token()


def test_invalid_client_is_a_configuration_error(tmp_path: Path) -> None:
    from portfolio_architect_gateway.errors import ConfigurationError, RemoteApiError

    class InvalidClient(FakeTransport):
        def oauth_refresh(self, **kwargs):
            raise RemoteApiError(
                400,
                "Comdirect API returned HTTP 400",
                operation="oauth_refresh",
                error_code="invalid_client",
            )

    with pytest.raises(ConfigurationError):
        _expired_client(tmp_path, InvalidClient()).ensure_access_token()


def test_malformed_refresh_response_remains_a_protocol_error(tmp_path: Path) -> None:
    class MalformedRefresh(FakeTransport):
        def oauth_refresh(self, **kwargs):
            return response({"refresh_token": "replacement-only"})

    with pytest.raises(ProtocolError):
        _expired_client(tmp_path, MalformedRefresh()).ensure_access_token()


def test_oauth_error_parser_retains_only_bounded_machine_code() -> None:
    from portfolio_architect_gateway.transport import _oauth_error_code

    assert _oauth_error_code(b'{"error":"invalid_grant","error_description":"secret detail"}', "application/json") == "invalid_grant"
    assert _oauth_error_code(b'{"error":"INVALID-GRANT"}', "application/json") is None
    assert _oauth_error_code(b'{"error":"invalid_grant","error":"other"}', "application/json") is None
    assert _oauth_error_code(b'not-json', "application/json") is None
