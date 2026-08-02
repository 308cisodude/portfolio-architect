# Portfolio Architect Gateway App v1.17.1

Version 1.17.1 is package-alignment only; the Gateway runtime is unchanged from v1.16.0.

Native Home Assistant App packaging for the read-only Portfolio Architect
Gateway. The App exposes no LAN port, uses an admin-only Ingress UI, runs the
long-lived process as UID/GID 65532, and keeps Comdirect and Gateway credentials
in App-private data.

Version 1.16.0 adds bounded discovery and explicit selection of one EUR
investment/settlement account. Only the conservative usable reserve and timestamp
enter the provider-neutral REST snapshot. Account identifiers, IBANs, labels,
transactions, and raw balance documents remain private.

Install updates in place. Do not uninstall the App or remove its data.
