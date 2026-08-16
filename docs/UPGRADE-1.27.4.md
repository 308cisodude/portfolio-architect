# Upgrade to Portfolio Architect 1.27.4

Version 1.27.4 is a narrow Comdirect resilience hotfix. It decouples short-lived
Comdirect OAuth session maintenance from the independently configured portfolio
snapshot cadence.

## Upgrade procedure

No config-entry, TLS-trust, dashboard, schema, or source migration is required.

1. Update Portfolio Architect through HACS to 1.27.4 and restart Home Assistant at a
   convenient time.
2. Update **Portfolio Architect Gateway — Comdirect** to 1.27.4 in place. Do not
   uninstall the App or remove its private data.
3. If Comdirect already reports `reauthentication_required`, complete one normal
   PhotoTAN bootstrap in the App Web UI. Do not reauthenticate merely because of the
   package upgrade when the existing session is healthy.
4. Confirm the Gateway returns to `status: ok`, `operating_mode: live`, and a verified
   snapshot after the next refresh.
5. The DKB and Trade Republic App packages are version-aligned to 1.27.4 but their
   provider behavior is unchanged; they may be updated in place normally.

## What changes

The Comdirect App now runs a provider-specific five-minute OAuth maintenance loop.
It checks the existing session independently of the 15-minute default portfolio
refresh cadence and performs an OAuth refresh only when the access token is no longer
inside the established safe-use window.

The maintenance path does not fetch holdings, balances, instruments, transactions,
or any order/payment capability. It only invokes the existing credential-isolated
OAuth renewal path and stores replacement session state in the existing App-private
session file.

A conclusive refresh-session rejection is latched for the running process until
interactive bootstrap succeeds, so the Gateway does not repeatedly submit a known
rejected refresh token every scheduled cycle.

## Preserved boundaries

- verified HTTPS/private CA trust: unchanged;
- Gateway bearer token: unchanged;
- no plaintext fallback;
- payload schema 8 / REST schema 1 / health schema 6: unchanged;
- portfolio polling cadence and snapshot freshness semantics: unchanged;
- `request_timeout_seconds`: unchanged by this release;
- Comdirect account selection and authorized investment cash: unchanged;
- Trade Republic statement import: unchanged;
- DKB remains experimental/manual-only/fail-closed;
- no trading, order, transfer, payment, or transaction-history capability.

No dashboard YAML migration is required.

Do not reauthenticate Comdirect solely because of this release when the current session is healthy.
