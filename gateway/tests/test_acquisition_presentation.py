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
