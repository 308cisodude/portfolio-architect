"""Read-only operator presentation for acquisition authority and method status.

The Gateway control plane remains authoritative.  This module deliberately renders
validated :class:`AcquisitionControl` state only; it owns no activation endpoint,
persists no state, and cannot alter acquisition authority or fallback policy.
"""

from __future__ import annotations

from html import escape
from typing import Final

from .acquisition_control import (
    AcquisitionControl,
    AcquisitionMethod,
    METHOD_READY,
)

ACQUISITION_AUTHORITY_CSS: Final = """
.pa-authority-intro{margin-bottom:14px}.pa-capability-grid,.pa-method-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}.pa-capability-card,.pa-method-card{border:1px solid #64748b55;border-radius:12px;padding:13px;background:#64748b0d}.pa-capability-card h3,.pa-method-card h3{margin:.1rem 0 .65rem;font-size:1.05rem}.pa-authority-row{display:flex;justify-content:space-between;gap:12px;align-items:baseline;margin:.45rem 0}.pa-authority-row span:first-child{opacity:.78}.pa-pill{display:inline-block;font-size:.76rem;font-weight:800;letter-spacing:.04em;padding:3px 8px;margin:2px 4px 2px 0;border-radius:999px;border:1px solid currentColor}.pa-pill.authority,.pa-pill.active{color:#4ade80}.pa-pill.ready{color:#60a5fa}.pa-pill.warning{color:#fbbf24}.pa-method-card.active,.pa-method-card.authority{border:2px solid #22c55eaa;background:#22c55e12}.pa-method-card.ready{border:2px solid #3b82f6aa;background:#3b82f612}.pa-method-card.warning{border:2px solid #f59e0baa;background:#f59e0b12}.pa-method-meta{font-size:.9rem;opacity:.86}.pa-supported{margin:.45rem 0}.pa-no-fallback{font-weight:800}.pa-authority-note{font-size:.9rem;opacity:.82}@media(max-width:600px){.pa-authority-row{display:block}.pa-authority-row span{display:block;margin-top:3px}}
""".strip()

_STATE_LABELS: Final = {
    "ready": "READY",
    "not_ready": "NOT READY",
    "unavailable": "UNAVAILABLE",
    "research_only": "RESEARCH ONLY",
}
_REASON_LABELS: Final = {
    "active_method": "active method",
    "provider_fixed": "provider fixed",
    "supplemental": "supplemental",
}
_CAPABILITY_LABELS: Final = {
    "holdings": "Holdings",
    "cash": "Cash",
}


def _method_css(method: AcquisitionMethod, *, authoritative: bool = False) -> str:
    if method.active:
        return "active"
    if authoritative:
        return "authority"
    if method.state == METHOD_READY:
        return "ready"
    return "warning"


def _method_state_label(method: AcquisitionMethod, *, authoritative: bool = False) -> str:
    if method.active and authoritative:
        return "ACTIVE · AUTHORITATIVE"
    if method.active:
        return "ACTIVE"
    if authoritative:
        return "AUTHORITATIVE · READY"
    return _STATE_LABELS.get(method.state, method.state.upper().replace("_", " "))


def _display_id(value: str) -> str:
    return escape(value)


def render_acquisition_authority(control: AcquisitionControl) -> str:
    """Render one bounded, read-only acquisition authority/status section."""
    methods = {item.method_id: item for item in control.methods}

    capability_cards: list[str] = []
    for item in control.capabilities:
        supported = "".join(
            '<span class="pa-pill {css}">{method} · {state}</span>'.format(
                css=_method_css(methods[method_id], authoritative=method_id == item.authoritative_method),
                method=_display_id(method_id),
                state=escape(_method_state_label(methods[method_id], authoritative=method_id == item.authoritative_method)),
            )
            for method_id in item.supported_methods
        )
        capability_cards.append(
            '<article class="pa-capability-card" data-capability="{capability}">'
            "<h3>{label}</h3>"
            '<div class="pa-authority-row"><span>Authoritative method</span>'
            '<span class="pa-pill authority">{authority}</span></div>'
            '<div class="pa-authority-row"><span>Authority reason</span>'
            "<strong>{reason}</strong></div>"
            '<div class="pa-authority-row"><span>Automatic fallback</span>'
            '<strong class="pa-no-fallback">{fallback}</strong></div>'
            '<div class="pa-supported"><span class="pa-authority-note">Supported methods</span><br>{supported}</div>'
            "</article>".format(
                capability=_display_id(item.capability_id),
                label=escape(_CAPABILITY_LABELS.get(item.capability_id, item.capability_id)),
                authority=_display_id(item.authoritative_method),
                reason=escape(_REASON_LABELS.get(item.authority_reason, item.authority_reason)),
                fallback=escape(item.fallback_policy),
                supported=supported,
            )
        )

    method_cards: list[str] = []
    for method in control.methods:
        authoritative_for = [
            _CAPABILITY_LABELS.get(item.capability_id, item.capability_id)
            for item in control.capabilities
            if item.authoritative_method == method.method_id
        ]
        is_authoritative = bool(authoritative_for)
        authority_text = ", ".join(authoritative_for) if authoritative_for else "none"
        method_cards.append(
            '<article class="pa-method-card {css}" data-method="{method}">'
            '<div class="pa-authority-row"><h3>{method}</h3>'
            '<span class="pa-pill {css}">{state}</span></div>'
            '<div class="pa-method-meta">Authoritative for: <strong>{authority}</strong><br>'
            'Can activate: <strong>{can_activate}</strong></div>'
            "</article>".format(
                css=_method_css(method, authoritative=is_authoritative),
                method=_display_id(method.method_id),
                state=escape(_method_state_label(method, authoritative=is_authoritative)),
                authority=escape(authority_text),
                can_activate="yes" if method.can_activate else "no",
            )
        )

    capability_html = (
        "".join(capability_cards)
        if capability_cards
        else '<p class="pa-authority-note">Capability authority is not advertised by this Gateway.</p>'
    )
    return (
        '<section class="pa-acquisition-authority" aria-labelledby="pa-acquisition-authority-heading">'
        '<h2 id="pa-acquisition-authority-heading">Acquisition authority</h2>'
        '<p class="pa-authority-intro">Read-only capability authority and method readiness. '
        'A supported method is not necessarily active or authoritative; authority changes only through '
        'the provider Gateway\'s explicit control path. Automatic fallback remains disabled.</p>'
        f'<div class="pa-capability-grid">{capability_html}</div>'
        '<h3>Method inventory</h3>'
        f'<div class="pa-method-grid">{"".join(method_cards)}</div>'
        '</section>'
    )
