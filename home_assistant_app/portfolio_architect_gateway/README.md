# Portfolio Architect Gateway — Comdirect v1.55.0

Version 1.55.0 keeps this historical `portfolio_architect_gateway` App available as the explicit migration source for the provider-qualified **Comdirect NEW** App. Its normal v1.53 atomic `live_api`/`csv` control plane remains unchanged until the operator deliberately stages and freezes an identity cut-over. The Gateway now applies `max_cached_snapshot_age_seconds` only to live acquisition: static CSV evidence remains servable with its original timestamp and Portfolio Architect's configured CSV freshness policy decides whether it is usable. The Home Assistant integration also gains method-aware anti-rollback handling for explicit schema-8 switches.

Version 1.53.0 adds the provider-neutral acquisition control plane and makes Comdirect the first explicitly switchable dual-method reference implementation. `live_api` and `csv` remain mutually exclusive with `fallback_policy: none`; inactive CSV becomes activatable only after both holdings and cash evidence are staged, and failed or interrupted switching restores the pre-switch control state. Interrupted-switch recovery discards an ambiguous canonical cache before startup refresh, while corrupt inactive CSV evidence is treated as not-ready without disrupting live acquisition. Portfolio Architect observes this state read-only through health schema 8.

Version 1.50.0 aligns the Comdirect App package with Portfolio Architect’s source-management UX milestone. Comdirect `live_api`/`csv` acquisition, static parsers, OAuth/session behavior and the live/static Ingress distinction are unchanged from the live-accepted v1.49.0 baseline.

Version 1.48.1 aligns the Comdirect App package with Portfolio Architect’s acquisition-aware freshness correction. Comdirect `live_api`/`csv` arbitration, static parsers, OAuth/session behavior and Ingress UX are unchanged from v1.48.0.

Version 1.48.0 adds explicit, mutually exclusive Comdirect acquisition modes while keeping `live_api` as the backward-compatible default.

## Live acquisition · Comdirect API

The established Comdirect API path continues to provide holdings and authorized investment cash through OAuth/PhotoTAN session handling. Automatic OAuth/session maintenance runs only while `live_api` is active. API failure never falls back to staged CSV evidence.

## Static acquisition · Comdirect CSV

The admin-only Ingress UI accepts independent depot holdings CSV and Girokonto cash CSV evidence. Static cash requires exactly one explicit opening balance and one explicit closing/current balance, with exact reconciliation through the transaction deltas; transaction rows are never persisted or used to invent cash when that reconciliation is absent. Raw CSVs, filenames, account/depot identifiers and transaction contents are transient. Only normalized private state is persisted.

CSV uploads may be staged while live mode remains active. They become authoritative only after an explicit mode switch. In CSV mode there is no automatic Comdirect API acquisition or OAuth/session maintenance and no fallback to the API.

Verified private-PKI HTTPS, bearer authentication, REST portfolio schema 1, health schema 8 (with schemas 1–7 compatibility), cash-authorization policy, LKG semantics and the read-only/advisory boundary remain intact. Upgrade in place and preserve `/data/gateway`.
