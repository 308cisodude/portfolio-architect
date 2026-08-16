# Supported versions

## Portfolio Architect

The current stable release and the immediately preceding stable release receive
security and correctness fixes while a documented upgrade path exists. Older
releases may continue to work but are not actively supported.

## Home Assistant

The 1.28.x release line requires Home Assistant 2026.7.0 or newer. CI validates
project tests on Python 3.14, HACS metadata, and the deliberately pinned hassfest
validator snapshot. The project targets the current and immediately previous
monthly Home Assistant release.

Scheduled HACS and hassfest workflows re-run the reviewed immutable validator
images. They do not silently adopt upstream image changes. Maintainers must review
and update those digests deliberately when validating against a newer upstream
snapshot.

## Gateway compatibility

Portfolio Architect 1.28.1 accepts REST portfolio schema 1, including the optional
additive `investment_cash` authorization metadata, and Gateway health schemas 1
through 6. Health schema 6 adds only bounded provider identity; schemas 1 through 5
remain available unchanged. Gateway App 1.16.1 and later remain compatible with the
legacy reserve contract; Gateway App 1.19.0 or newer is required to configure cash
authorization policies, and 1.19.1 or newer contains the corrected
capped-to-all-available Ingress transition. Gateway App 1.28.1 is version-aligned with the current stable integration.
Comdirect remains the stable live provider. DKB remains experimental/manual-only and non-live; v1.28.0 adds only a registration-gated anonymous FinTS BPD capability probe. Trade Republic retains the v1.25 documented local `DEPOTAUSZUG` statement-import family and serves accepted holdings through REST schema 1; in v1.26 its App auto-starts and Portfolio Architect can consume it as an additional authenticated Gateway alongside the existing primary REST source. Version 1.26.1 corrects target matching for ISIN-only provider snapshots without changing either wire schema. Version 1.26.2 adds Home Assistant presentation/diagnostic metadata. Version 1.26.3 is a dashboard/presentation follow-up and keeps both wire schemas unchanged. Version 1.26.4 attempted native date-tile formatting; Version 1.26.5 adds only read-only Home Assistant `date.*` presentation counterparts and likewise keeps both wire schemas unchanged. Version 1.26.6 fixes non-live REST Gateway source identification. Version 1.26.7 fixes cached-snapshot quantity persistence and HTTP validator precedence. Version 1.27.1 is the first successfully published form of the verified private-PKI HTTPS transport; live acceptance then exposed that the manifest-level `single_config_entry` gate prevented Supervisor discovery from reaching an already-configured entry. Version 1.27.2 fixes that Home Assistant config-flow eligibility issue while retaining the same TLS/runtime contracts. Version 1.27.3 fixes the residual DKB Gateway `dkb` versus DKB CSV `dkb_csv` discovery-suppression mismatch without changing TLS/runtime contracts. Version 1.27.4 keeps those contracts and moves short-lived Comdirect OAuth renewal onto a provider-specific maintenance cadence independent of portfolio polling. Version 1.28.0 keeps the same wire/TLS contracts and adds only the DKB anonymous FinTS capability-probe milestone; DKB live holdings remain disabled pending product registration and authenticated user-capability validation. Version 1.28.1 refreshes the immutable GitHub Actions runtime pins only; provider runtime, wire/TLS contracts and the DKB gate remain unchanged. Legacy HTTP remains supported only as a bounded in-place migration state when upgrading from pre-v1.27 installations.

## Security fixes

A release that repairs a security vulnerability will document the affected
versions and remediation path in the corresponding security advisory. Users
should not rely on an unsupported release merely because it still starts.
