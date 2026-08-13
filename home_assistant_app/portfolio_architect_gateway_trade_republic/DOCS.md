# Portfolio Architect Gateway — Trade Republic v1.24.1

This is the separately installable Trade Republic provider App boundary introduced in Portfolio Architect 1.24.0 and fixed for startup in 1.24.1.

It is deliberately **not yet a live portfolio source**. Its purpose in this release is to establish the independent Supervisor identity, private storage, read-only authenticated Gateway server, bounded `provider_id: trade_republic`, and future in-place upgrade path.

The App is marked **experimental** and **manual-only** so installing it does not start a non-functional background service automatically. If started for acceptance testing, the Ingress page reports the provider package state and the REST health endpoint reports a degraded/unavailable provider with no portfolio snapshot.

No credentials, bank documents or account identifiers are requested or persisted in this release. Do not configure Portfolio Architect to consume this endpoint yet.
