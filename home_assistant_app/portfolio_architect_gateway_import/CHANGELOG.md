# Changelog

## 1.56.0

Bearer token moves to a lower collapsed sensitive section; exact Supervisor discovery UUID lifecycle cleanup/reconciliation is added; routine Ingress request-completion logging moves to DEBUG.

## 1.55.1

- Version alignment only for the v1.55.1 Comdirect migration hotfix; Generic Import CSV behavior and experimental maturity are unchanged.

## 1.55.0

- Version-aligns the experimental Generic Import App with the Comdirect App-identity migration release.
- Mapped-CSV acquisition, transient raw-input handling, provider identity and freshness behavior are unchanged from v1.54.0.

## 1.54.0

- Standardizes the authoritative mapped-CSV acquisition card to green with an explicit ACTIVE badge.
- Removes the misleading user-facing Gateway cache/freshness option for static CSV acquisition; Portfolio Architect remains authoritative for evidence freshness.
- Replaces the brittle exact Alpine OpenSSL package revision pin with branch-current installation plus a protected CI security floor.

## 1.53.1

- Refresh the pinned Alpine 3.24 OpenSSL runtime CLI dependency to `3.5.8-r0` after repository package rotation; private-PKI generation and TLS behavior are unchanged.
- Keep accepted Generic Import CSV snapshots servable independently of the legacy Gateway cache-age setting; Portfolio Architect's CSV freshness policy remains authoritative.
- Preserve transient raw CSV handling, fixed `generic_csv` identity and read-only holdings-only semantics.

## 1.53.0

- Add health-schema-8 acquisition control metadata for the fixed `csv` method.
- Keep mapped-CSV acquisition, fixed `generic_csv` identity and read-only boundary unchanged.

## 1.52.0

- Keep Generic Import explicitly experimental pending deliberate live Home Assistant exercise.
- Align package metadata with Portfolio Architect v1.52.0 and document a safe synthetic standalone smoke that does not join the real portfolio source set.
- Mapped-CSV parsing, transient raw input, fixed `generic_csv` identity and canonical holdings-only persistence are unchanged from v1.51.1.

## 1.51.1

- Aligns package metadata with the Portfolio Architect v1.51.1 Home Assistant integration hotfix; Generic Import acquisition/runtime behavior is unchanged from v1.51.0.

## 1.51.0

- Introduce the isolated Generic Import Gateway for provider-neutral mapped CSV holdings.
- Keep raw CSV bytes transient and persist only one canonical snapshot plus bounded private mapping/diagnostic state.
- Publish provider identity `generic_csv` with acquisition mode `csv` over verified private-PKI HTTPS.
