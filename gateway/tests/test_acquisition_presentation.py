from datetime import datetime, timedelta, timezone

from portfolio_architect_gateway.acquisition_control import (
    AUTHORITY_ACTIVE_METHOD,
    AUTHORITY_PROVIDER_FIXED,
    METHOD_READY,
    METHOD_RESEARCH_ONLY,
    METHOD_UNAVAILABLE,
    AcquisitionControl,
    AcquisitionMethod,
    capability,
)
from portfolio_architect_gateway.acquisition_presentation import render_acquisition_authority


def test_authority_presentation_distinguishes_authority_readiness_and_activation() -> None:
    control = AcquisitionControl(
        active_method="live_api",
        methods=(
            AcquisitionMethod("live_api", METHOD_READY, True, True),
            AcquisitionMethod("csv", METHOD_READY, False, True),
        ),
        capabilities=(
            capability(
                "holdings",
                "live_api",
                "live_api",
                "csv",
                authority_reason=AUTHORITY_ACTIVE_METHOD,
            ),
            capability(
                "cash",
                "live_api",
                "live_api",
                "csv",
                authority_reason=AUTHORITY_ACTIVE_METHOD,
            ),
        ),
    )

    html = render_acquisition_authority(control)

    assert 'id="pa-acquisition-authority-heading">Acquisition authority</h2>' in html
    assert 'data-capability="holdings"' in html
    assert 'data-capability="cash"' in html
    assert html.count('class="pa-pill authority">live_api</span>') == 2
    assert 'live_api · ACTIVE · AUTHORITATIVE' in html
    assert 'csv · READY' in html
    assert 'data-method="live_api"' in html
    assert 'data-method="csv"' in html
    assert 'Authoritative for: <strong>Holdings, Cash</strong>' in html
    assert 'Can activate: <strong>yes</strong>' in html
    assert html.count('class="pa-no-fallback">none</strong>') == 2
    assert "supported method is not necessarily active or authoritative" in html
    assert "Automatic fallback remains disabled" in html
    assert "<form" not in html
    assert "<button" not in html


def test_authority_presentation_keeps_research_and_unavailable_methods_non_authoritative() -> None:
    control = AcquisitionControl(
        active_method="csv",
        methods=(
            AcquisitionMethod("csv", METHOD_READY, True, True),
            AcquisitionMethod("fints", METHOD_RESEARCH_ONLY, False, False),
            AcquisitionMethod("live_api", METHOD_UNAVAILABLE, False, False),
        ),
        capabilities=(
            capability(
                "holdings",
                "csv",
                "csv",
                "fints",
                "live_api",
                authority_reason=AUTHORITY_PROVIDER_FIXED,
            ),
        ),
    )

    html = render_acquisition_authority(control)

    assert 'class="pa-pill authority">csv</span>' in html
    assert "provider fixed" in html
    assert "fints · RESEARCH ONLY" in html
    assert "live_api · UNAVAILABLE" in html
    assert 'data-method="fints"' in html
    assert 'data-method="live_api"' in html
    assert html.count('Can activate: <strong>no</strong>') == 2
    assert 'Authoritative for: <strong>none</strong>' in html


def test_supplemental_authority_is_visually_authoritative_even_when_not_provider_active() -> None:
    from portfolio_architect_gateway.acquisition_control import AUTHORITY_SUPPLEMENTAL

    control = AcquisitionControl(
        active_method="live_api",
        methods=(
            AcquisitionMethod("live_api", METHOD_READY, True, True),
            AcquisitionMethod("statement", METHOD_READY, False, True),
        ),
        capabilities=(
            capability(
                "holdings",
                "live_api",
                "live_api",
                authority_reason=AUTHORITY_ACTIVE_METHOD,
            ),
            capability(
                "cash",
                "statement",
                "live_api",
                "statement",
                authority_reason=AUTHORITY_SUPPLEMENTAL,
            ),
        ),
    )

    html = render_acquisition_authority(control)

    assert 'statement · AUTHORITATIVE · READY' in html
    assert 'class="pa-method-card authority" data-method="statement"' in html
    assert 'Authoritative for: <strong>Cash</strong>' in html


def test_authority_presentation_shows_independent_authoritative_evidence_clocks() -> None:
    control = AcquisitionControl(
        active_method="pdf",
        methods=(
            AcquisitionMethod("pdf", METHOD_READY, True, True),
            AcquisitionMethod("live_api", METHOD_UNAVAILABLE, False, False),
        ),
        capabilities=(
            capability(
                "holdings",
                "pdf",
                "pdf",
                "live_api",
                authority_reason=AUTHORITY_PROVIDER_FIXED,
            ),
            capability(
                "cash",
                "pdf",
                "pdf",
                "live_api",
                authority_reason=AUTHORITY_PROVIDER_FIXED,
            ),
        ),
    )
    holdings_at = datetime(2026, 8, 19, 9, 17, 29, tzinfo=timezone.utc)
    cash_at = datetime(2026, 8, 20, 21, 59, 59, tzinfo=timezone.utc)

    html = render_acquisition_authority(
        control,
        evidence_timestamps={"holdings": holdings_at, "cash": cash_at},
    )

    assert html.count('class="pa-pill evidence-available">AVAILABLE</span>') == 2
    assert holdings_at.isoformat(timespec="seconds") in html
    assert cash_at.isoformat(timespec="seconds") in html
    assert "currently published authoritative snapshot" in html
    assert "inactive staged evidence" in html


def test_authority_presentation_marks_missing_capability_evidence_without_changing_authority() -> None:
    control = AcquisitionControl(
        active_method="csv",
        methods=(AcquisitionMethod("csv", METHOD_READY, True, True),),
        capabilities=(
            capability(
                "holdings",
                "csv",
                "csv",
                authority_reason=AUTHORITY_PROVIDER_FIXED,
            ),
        ),
    )

    html = render_acquisition_authority(
        control, evidence_timestamps={"holdings": None}
    )

    assert 'class="pa-pill authority">csv</span>' in html
    assert 'class="pa-pill evidence-missing">NOT AVAILABLE</span>' in html
    assert "Evidence timestamp" in html
    assert "not available" in html
