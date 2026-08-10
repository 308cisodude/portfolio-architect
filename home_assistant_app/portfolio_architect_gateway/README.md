# Portfolio Architect Gateway App v1.19.0

Native Home Assistant App packaging for the read-only Comdirect Gateway. The App
exposes no LAN port, uses an admin-only Ingress UI, runs the long-lived process as
UID/GID 65532, and keeps Comdirect and Gateway credentials in App-private data.

Version 1.19.0 adds **Investment cash authorization**. After explicitly selecting
an eligible EUR account, the Gateway distinguishes the booked account balance,
eligible non-borrowed cash, and the amount Portfolio Architect may allocate.

The default policy is **All eligible cash**, preserving existing behavior. A
**Cap eligible cash** policy can instead limit authorization to a configured EUR
amount. Invalid capped policy state fails closed.

The provider-neutral REST snapshot may contain bounded monetary cash metadata,
but account identifiers, IBANs, labels, account-holder data, transactions, credit
limits, and raw bank response documents remain private.

Install updates in place. Do not uninstall the App or remove its data.
