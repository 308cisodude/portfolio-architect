# Changelog

## 1.51.1

- Aligns package metadata with the Portfolio Architect v1.51.1 Home Assistant integration hotfix; Generic Import acquisition/runtime behavior is unchanged from v1.51.0.

## 1.51.0

- Introduce the isolated Generic Import Gateway for provider-neutral mapped CSV holdings.
- Keep raw CSV bytes transient and persist only one canonical snapshot plus bounded private mapping/diagnostic state.
- Publish provider identity `generic_csv` with acquisition mode `csv` over verified private-PKI HTTPS.
