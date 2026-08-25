# Changelog

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
