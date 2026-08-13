# Portfolio Architect Gateway App v1.21.0

Native Home Assistant App packaging for the read-only Comdirect Gateway. The App
exposes no LAN port, uses an admin-only Ingress UI, runs the long-lived process as
UID/GID 65532, and keeps Comdirect and Gateway credentials in App-private data.

Version 1.21.0 aligns the App package with Portfolio Architect's execution-semantics release. Gateway banking behavior and wire contracts remain unchanged from 1.20.1. REST schema 1, health schema 5, authentication, and cash-policy behavior remain unchanged.

Version 1.19.1 fixes the **Investment cash authorization** transition from a capped policy back to all eligible cash. Version 1.19.0 introduced the feature. After explicitly selecting
an eligible EUR account, the Gateway distinguishes the booked account balance,
eligible non-borrowed cash, and the amount Portfolio Architect may allocate.

The default policy is **All eligible cash**, preserving existing behavior. A
**Cap eligible cash** policy can instead limit authorization to a configured EUR
amount. Invalid capped policy state fails closed. For `all_available`, the server ignores any stale cap field and persists the canonical no-cap policy; the Ingress UI clearing/disabling behavior is only a usability aid.

The provider-neutral REST snapshot may contain bounded monetary cash metadata,
but account identifiers, IBANs, labels, account-holder data, transactions, credit
limits, and raw bank response documents remain private.

Install updates in place. Do not uninstall the App or remove its data.
