# Changelog

## 1.51.0

- Introduce the isolated Generic Import Gateway for provider-neutral mapped CSV holdings.
- Keep raw CSV bytes transient and persist only one canonical snapshot plus bounded private mapping/diagnostic state.
- Publish provider identity `generic_csv` with acquisition mode `csv` over verified private-PKI HTTPS.
