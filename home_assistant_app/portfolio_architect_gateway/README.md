# Portfolio Architect Gateway — Comdirect v1.48.0

Version 1.48.0 adds explicit, mutually exclusive Comdirect acquisition modes while keeping `live_api` as the backward-compatible default.

## Live acquisition · Comdirect API

The established Comdirect API path continues to provide holdings and authorized investment cash through OAuth/PhotoTAN session handling. Automatic OAuth/session maintenance runs only while `live_api` is active. API failure never falls back to staged CSV evidence.

## Static acquisition · Comdirect CSV

The admin-only Ingress UI accepts independent depot holdings CSV and Girokonto cash CSV evidence. Static cash requires exactly one explicit opening balance and one explicit closing/current balance, with exact reconciliation through the transaction deltas; transaction rows are never persisted or used to invent cash when that reconciliation is absent. Raw CSVs, filenames, account/depot identifiers and transaction contents are transient. Only normalized private state is persisted.

CSV uploads may be staged while live mode remains active. They become authoritative only after an explicit mode switch. In CSV mode there is no automatic Comdirect API acquisition or OAuth/session maintenance and no fallback to the API.

Verified private-PKI HTTPS, bearer authentication, REST portfolio schema 1, health schema 7 (with schemas 1–6 compatibility), cash-authorization policy, LKG semantics and the read-only/advisory boundary remain intact. Upgrade in place and preserve `/data/gateway`.
