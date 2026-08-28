# Portfolio Architect 1.55.1

Portfolio Architect v1.55.1 is a narrow live-migration hotfix prepared from the exact published v1.55.0 tracked-source baseline. It fixes the first real Comdirect App-identity migration attempt without changing the v1.55 security model, provider identity, wire schemas, acquisition semantics, freshness policy, private-PKI trust model, planner behavior, or advisory-only boundary.

## Live-observed v1.55.0 defect

The published v1.55.0 migration exporter accepted only the historical schema-1 `comdirect-acquisition.json` shape. A normal production Comdirect installation that had previously exercised the explicit v1.53 acquisition control plane can legitimately persist schema 2 with `previous_mode`, `last_method_change_at`, and `last_method_change_reason`. The production installation therefore failed local export validation before any migration request reached Comdirect NEW.

The failure was fail-closed and non-destructive: the historical App remained live and authoritative, Comdirect NEW remained in its pristine waiting state, Portfolio Architect did not change endpoints, and no private migration state was committed. The legacy Ingress nevertheless reduced the bounded validation failure to a bare HTTP 400, producing poor operator diagnostics.

## Fix

v1.55.1:

- accepts both currently supported persisted Comdirect acquisition-state schemas 1 and 2, with schema-2 fields validated as strictly as the live acquisition runtime validates them;
- keeps `comdirect-session.json` excluded and still requires fresh PhotoTAN bootstrap on Comdirect NEW before a migrated `live_api` endpoint can become discoverable;
- validates the one-time migration code and legacy state locally, then performs an authenticated fingerprint-pinned successor status preflight before transferring any private state;
- supports idempotent recovery when the successor already has an exactly matching staged or committed summary but the historical App has not yet recorded its local staged marker;
- classifies migration failures into a small privacy-safe reason set and returns to the legacy migration card instead of exposing a generic HTTP 400 page;
- never exposes exception text, filenames, bearer secrets, OAuth material, client credentials, account/depot identifiers, response bodies, or other bank data in those reason classes;
- leaves the exact historical→provider-qualified hostname relationship, same-CA requirement, existing Gateway bearer token, explicit legacy freeze, explicit PA confirmation, and health/snapshot-integrity validation unchanged.

The bounded legacy-side reason classes are `invalid_code`, `legacy_state_invalid`, `successor_unreachable`, `successor_tls_mismatch`, `successor_auth_rejected`, `successor_payload_rejected`, `successor_response_invalid`, and `local_stage_record_failed`.

## Compatibility

The following established contracts remain unchanged in v1.55.1:

- canonical provider identity `comdirect`;
- payload schema 8;
- REST portfolio schema 1;
- Gateway health schema 8 current, schemas 1–7 accepted;
- presentation schema 2 and broker schemas 1/2/3;
- explicit Comdirect `live_api`/CSV arbitration with `fallback_policy: none`;
- Trade Republic PDF, DKB CSV and Generic Import CSV acquisition behavior;
- Portfolio Architect evidence-kind freshness and Gateway live-LKG semantics;
- verified private-PKI HTTPS, bearer authentication, hostname verification and local-source/DNS hardening;
- authenticated DKB FinTS acquisition remains disabled;
- no trading, order, transfer, payment or transaction-history capability.

No dashboard YAML replacement is required. Follow `docs/UPGRADE-1.55.1.md` for the resumed migration.

## Preserved historical release-note contracts

For regression continuity, this hotfix preserves the established compatibility statements: payload schema 8: unchanged; REST portfolio schema 1: unchanged; Gateway health schema 8 current; schemas 1–7 remain supported (and therefore schemas 1–6 remain supported); presentation schema 2; broker schemas 1/2/3. It does not move PDF parsing into Portfolio Architect.

The former v1.19.0-rc2 brokerage-probe experiment is not promoted by this release. The v1.33.0 source-freshness and plan-schedule separation remains intact: scheduling is anchored to the latest valid Portfolio Architect evaluation and this hotfix does not change any configured freshness threshold. Dashboard changes are not included.

No trading, order, transfer, payment, or transaction-history capability is added.
