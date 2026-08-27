# Portfolio Architect 1.54.0

Portfolio Architect v1.54.0 is a Gateway presentation and release-engineering cleanup prepared from the published and fully live-accepted v1.53.1 baseline. It does not change provider acquisition semantics, Portfolio Architect freshness thresholds, Gateway health schema 8, REST portfolio schema 1, private-PKI transport or planner behavior.

## Consistent acquisition-state colours

Every provider App now uses the same visual meaning for acquisition status:

- green: the authoritative ACTIVE acquisition method;
- blue: an inactive method that is ready and can be activated;
- amber: unavailable, not-ready or research-only acquisition.

This fixes the Comdirect inversion where active Live API was blue while the inactive CSV section could appear green. Trade Republic, DKB and Generic Import now use the same semantic classes rather than provider-specific colour meaning.

## One freshness-policy authority

The v1.53.1 static-retention fix established the intended architecture: active static CSV/PDF evidence remains servable with its original evidence timestamp and Portfolio Architect decides whether that evidence is fresh enough for planning. v1.54.0 therefore removes `max_cached_snapshot_age_seconds` from the user-facing configuration schema of the static-only DKB, Trade Republic and Generic Import Apps.

The common static-App parser continues to accept the retired bounded key as a compatibility bridge for existing Supervisor option state, but it has no effect on active static evidence. No new freshness policy is introduced.

Comdirect retains the same underlying cache-age option because live acquisition can legitimately use bounded last-known-good serving during provider failure. Its Home Assistant configuration label is now **Maximum live LKG snapshot age**, and the Comdirect Live API Ingress section explicitly states that the setting is a Gateway resilience limit only. Portfolio Architect remains authoritative for planning freshness.

## Alpine runtime-package policy

The v1.53.1 publication preparation demonstrated that exact-pinning an APK revision from a mutable Alpine branch is brittle: Alpine retired `openssl=3.5.7-r0` and moved to `3.5.8-r0`, causing a source-correct Docker build to fail until the release candidate was amended. v1.54.0 replaces exact `openssl=<apk revision>` installation with branch-current `apk add --no-cache openssl` in all four provider Apps.

This does not relax the immutable boundaries that are actually stable: the Python/Alpine base image remains digest-pinned, GitHub Actions remain full-SHA pinned, and Python dependencies remain exact-version/hash locked. Protected validation and immutable-publication Docker builds now inspect the installed OpenSSL CLI and fail if it is older than 3.5.8; the resolved runtime version is written into the workflow step summary as build evidence. The source SPDX SBOM records the Alpine OpenSSL package identity plus the reviewed minimum instead of falsely claiming an exact mutable repository revision.

## Historical compatibility references

The v1.33.0 source-freshness and plan-schedule separation remains anchored to the latest valid Portfolio Architect evaluation; v1.54.0 does not change any configured freshness threshold. The later v1.39 colourful allocation view was not included in v1.38.1; that historical sequencing remains unchanged.

The long-lived regression suite keeps the following published compatibility statements explicit: `payload schema 8: unchanged`; `REST portfolio schema 1: unchanged`; `Gateway health schema 8 current; schemas 1–7 remain supported`; older health `schemas 1–6 remain supported`; presentation schema 2 and broker schemas 1/2/3 remain unchanged. The historical v1.19.0-rc2 brokerage-probe exclusion remains retired and is not promoted by this release. The authenticated DKB FinTS acquisition remains disabled. The release does not move PDF parsing into Portfolio Architect; provider-specific statement parsing remains inside the Trade Republic Gateway. **No trading, order, transfer, payment, or transaction-history capability** is introduced.

## Preserved contracts

- Home Assistant provider/source configuration: unchanged
- REST portfolio schema: 1
- Gateway health schema: 8; schemas 1-7 remain accepted
- historical payload schema 8 compatibility contract: unchanged
- Comdirect `live_api` / `csv` explicit no-fallback arbitration: unchanged
- Trade Republic PDF, DKB CSV and Generic Import CSV acquisition: unchanged
- DKB anonymous FinTS research gate: unchanged; authenticated DKB FinTS remains disabled
- private-CA verified HTTPS and bearer authentication: unchanged
- evidence timestamps and Portfolio Architect freshness thresholds: unchanged
- planner, funding and execution-path semantics: unchanged
- no trading, order, transfer, payment, sell or withdrawal capability

No dashboard YAML replacement is required.
