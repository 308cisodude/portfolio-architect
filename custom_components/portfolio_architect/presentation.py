"""Dashboard-facing presentation helpers.

The Home Assistant entity states remain stable machine-readable values.  The
reference dashboards may be used in a frontend whose global language differs
from the dashboard language, so they consume these explicit presentation
attributes instead of relying on frontend locale translation for state values.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

_NOT_AVAILABLE_DE = "Nicht verfügbar"

_STATE_DE: dict[str, dict[str, str]] = {
    "plan_change": {
        "baseline_established": "Ausgangsbasis gespeichert",
        "unchanged": "Keine wesentliche Änderung",
        "allocation_changed": "Allokation geändert",
        "recommendation_changed": "Empfehlung geändert",
        "execution_state_changed": "Ausführungsstatus geändert",
        "policy_changed": "Richtlinienstatus geändert",
        "source_changed": "Quelle geändert",
        "multiple_changes": "Mehrere Änderungen",
    },
    "plan_frequency": {
        "weekly": "Wöchentlich",
        "monthly": "Monatlich",
        "quarterly": "Vierteljährlich",
        "yearly": "Jährlich",
    },
    "plan_budget_basis": {
        "per_period": "Je Periode",
        "per_execution": "Je Ausführung",
    },
    "execution_policy": {
        "legacy_distribution": "Bisherige Verteilung",
        "monthly_continuity": "Monatliche Kontinuität",
        "balanced": "Ausgewogen",
        "efficiency_first": "Effizienz zuerst",
    },
    "execution_state": {
        "ready": "Bereit zur Investition",
        "waiting_for_reserve": "Wartet auf Anlageguthaben",
        "deferred_for_cost_efficiency": "Für Kosteneffizienz zurückgestellt",
        "no_eligible_purchase": "Kein geeigneter Kauf",
        "reserve_unavailable": "Anlageguthaben nicht verfügbar",
    },
    "plan_actionability": {
        "actionable_now": "Jetzt umsetzbar",
        "scheduled": "Geplant",
        "overdue_actionable": "Überfällig, aber umsetzbar",
        "not_ready": "Nicht bereit",
        "not_actionable": "Nicht umsetzbar",
    },
    "gateway_status": {
        "ok": "OK",
        "degraded": "Eingeschränkt",
        "unavailable": _NOT_AVAILABLE_DE,
    },
    "gateway_operating_mode": {
        "live": "Live",
        "last_known_good": "Letzter gültiger Stand",
        "reauthentication_required": "Neuanmeldung erforderlich",
        "unavailable": _NOT_AVAILABLE_DE,
    },
    "gateway_refresh_schedule": {
        "scheduled": "Geplant",
        "due_now": "Jetzt fällig",
        "overdue": "Überfällig",
        "refreshing": "Wird aktualisiert",
    },
    "gateway_last_refresh_trigger": {
        "startup": "Start",
        "scheduled": "Geplant",
        "manual": "Manuell",
        "bootstrap": "Erstanmeldung",
    },
    "gateway_attention_reason": {
        "none": "Keiner",
        "health_unavailable": "Status nicht erreichbar",
        "reauthentication_required": "Neuanmeldung erforderlich",
        "integrity_failure": "Integritätsfehler",
        "supplemental_source_unavailable": "Zusätzliche Quelle nicht verfügbar",
        "snapshot_unavailable": "Datenstand nicht verfügbar",
        "refresh_overdue": "Aktualisierung überfällig",
        "last_known_good": "Letzter gültiger Datenstand",
        "authentication_error": "Authentifizierungsfehler",
        "rate_limited": "Anfragerate begrenzt",
        "remote_service_error": "Fehler des externen Dienstes",
        "remote_api_error": "Fehler der externen API",
        "transport_error": "Verbindungsfehler",
        "invalid_response": "Ungültige Antwort des externen Dienstes",
        "configuration_error": "Konfigurationsfehler",
        "gateway_error": "Gateway-Fehler",
        "internal_error": "Interner Fehler",
    },
    "gateway_recommended_action": {
        "none": "Keine",
        "reauthenticate": "Mit PhotoTAN neu anmelden",
        "wait": "Automatischen Neuversuch abwarten",
        "check_connectivity": "Verbindung prüfen",
        "inspect_logs": "Gateway-Protokoll prüfen",
        "fix_configuration": "Gateway-Konfiguration korrigieren",
    },
}


def display_state_de(kind: str, state: str | None, *, available: bool = True) -> str:
    """Return one bounded German state label for the reference dashboard."""
    if not available or state is None:
        return _NOT_AVAILABLE_DE
    return _STATE_DE.get(kind, {}).get(state, state)


def display_binary_state_de(kind: str, is_on: bool) -> str:
    """Return German presentation text for dashboard binary-state values."""
    values = {
        "data_fresh": ("Im Aktualitätsfenster", "Außerhalb des Aktualitätsfensters"),
        "source_healthy": ("Verfügbar", "Nicht verfügbar"),
    }
    on_text, off_text = values.get(kind, ("Ja", "Nein"))
    return on_text if is_on else off_text


def display_datetime_de(value: datetime | None) -> str:
    """Render an absolute local timestamp without depending on frontend locale."""
    if value is None:
        return _NOT_AVAILABLE_DE
    return value.strftime("%d.%m.%Y %H:%M")


def display_eur_de(value: Any, *, available: bool = True) -> str:
    """Render one EUR amount using German separators for the reference dashboard."""
    if not available or value is None:
        return _NOT_AVAILABLE_DE
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return _NOT_AVAILABLE_DE
    text = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} €"


def display_eur_en(value: Any, *, available: bool = True) -> str:
    """Render one EUR amount using English separators for dashboard context."""
    if not available or value is None:
        return "Unavailable"
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "Unavailable"
    return f"€{amount:,.2f}"


def investment_cash_totals(
    provider_cash: Iterable[Any],
    *,
    fallback_eligible: Any | None,
    fallback_authorized: Any | None,
) -> tuple[float, float] | None:
    """Return total eligible and policy-excluded cash when evidence is complete."""
    providers = tuple(provider_cash)
    if providers:
        if any(item.eligible_eur is None or item.authorized_eur is None for item in providers):
            return None
        eligible = sum((Decimal(str(item.eligible_eur)) for item in providers), Decimal("0"))
        authorized = sum((Decimal(str(item.authorized_eur)) for item in providers), Decimal("0"))
    elif fallback_eligible is not None and fallback_authorized is not None:
        eligible = Decimal(str(fallback_eligible))
        authorized = Decimal(str(fallback_authorized))
    else:
        return None
    cents = Decimal("0.01")
    eligible = eligible.quantize(cents)
    excluded = max(Decimal("0"), eligible - authorized).quantize(cents)
    return float(eligible), float(excluded)


def display_investment_cash_context(
    total_available: Any,
    policy_excluded: Any,
    *,
    planned_outlay: Any | None = None,
    german: bool,
) -> str:
    """Render bounded policy context for authorized/remaining investment cash."""
    if german:
        parts = [
            f"von {display_eur_de(total_available)} verfügbarem Bargeld",
            f"{display_eur_de(policy_excluded)} per Richtlinie ausgeschlossen",
        ]
        if planned_outlay is not None and Decimal(str(planned_outlay)) > Decimal("0.005"):
            parts.append(f"{display_eur_de(planned_outlay)} geplant")
    else:
        parts = [
            f"of {display_eur_en(total_available)} available cash",
            f"{display_eur_en(policy_excluded)} excluded by policy",
        ]
        if planned_outlay is not None and Decimal(str(planned_outlay)) > Decimal("0.005"):
            parts.append(f"{display_eur_en(planned_outlay)} planned")
    return " · ".join(parts)


def display_count_de(value: int | None, *, available: bool = True) -> str:
    """Render a bounded count or the explicit unavailable label."""
    if not available or value is None:
        return _NOT_AVAILABLE_DE
    return str(value)


def unavailable_source_label(source_id: str, *, german: bool) -> str:
    """Return a bounded privacy-safe source label without endpoint/path details."""
    if source_id.startswith("gateway:"):
        provider_id = source_id.split(":", 1)[1]
        known = {
            "comdirect": "Comdirect",
            "dkb": "DKB",
            "trade_republic": "Trade Republic",
            "local_rest_json": "Local REST",
        }
        provider = known.get(provider_id, provider_id.replace("_", " ").title())
        if german:
            if provider == "Trade Republic":
                return "Trade-Republic-Gateway"
            return f"{provider}-Gateway"
        return f"{provider} Gateway"
    return "Supplemental source" if not german else "Zusätzliche Quelle"


def unavailable_source_summary(source_ids: tuple[str, ...], *, german: bool) -> str:
    """Render a compact privacy-safe summary for one or more failed sources."""
    labels = tuple(unavailable_source_label(item, german=german) for item in source_ids)
    if labels:
        return " · ".join(labels)
    return "Keine" if german else "None"
