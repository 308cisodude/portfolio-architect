# Portfolio Architect 1.53.1

Portfolio Architect v1.53.1 is a narrow live-acceptance hotfix on top of the published v1.53.0 provider-acquisition control plane. It keeps provider identity, health schema 8, REST portfolio schema 1 and the explicit no-fallback arbitration model unchanged.

## Method-aware timestamp anti-rollback

The pre-v1.53 coordinator correctly rejected any primary or supplemental snapshot whose `generated_at` moved backwards. With explicit acquisition switching, however, a legitimate static CSV/PDF evidence set may predate the most recently accepted live snapshot. v1.53.1 keeps timestamp monotonicity strict inside one acquisition method but permits one older evidence timeline only when validated health-schema-8 control history proves all of the following: the current method differs from the last accepted method, `previous_acquisition_method` equals that last accepted method, the change reason is `operator`, and the recorded explicit change happened no earlier than the previously accepted snapshot. Older health schemas, same-method rollback, stale/incomplete switch history and automatic fallback remain rejected.

The rule is applied symmetrically to the primary Gateway and supplemental Gateways so future provider methods do not reintroduce the same defect.

## Primary-source attribution while HA LKG is active

If Portfolio Architect itself rejects the primary REST snapshot on integrity/acceptance grounds while the Gateway health document is otherwise live, the bounded unavailable-source set now identifies that primary Gateway. The dashboard/entity therefore renders the provider label (for example `Comdirect Gateway`) instead of `None`. Existing v1.26.6 behavior for Gateway-local reauthentication/LKG remains unchanged.

## Static evidence is not expired by the live cache TTL

The historical Gateway `max_cached_snapshot_age_seconds` value is now an effective retention limit only for live acquisition methods. Active `csv` and `pdf` methods always serve their accepted canonical snapshot with the original immutable evidence timestamp. Portfolio Architect's evidence-kind freshness policy remains the authority that decides whether static evidence is usable.

This applies to Comdirect CSV, DKB CSV, Trade Republic PDF and Generic Import CSV. New static-only App configurations default the legacy cache-age option to `0`; existing non-zero settings are safe because the runtime reports and applies an effective value of `0` while a static method is active. Switching Comdirect back to `live_api` restores its configured bounded live-cache retention automatically.

## Supplemental unavailability is not an integrity mismatch

A supplemental Gateway health document that reports no servable snapshot is classified as `snapshot_unavailable` before the snapshot fetch. A race where the snapshot endpoint returns HTTP 503 is represented by the same bounded class. Neither path creates a snapshot-integrity repair. True provider identity, timestamp, position-count and SHA-256 inconsistencies remain fail-closed integrity errors.

## Provider-App build dependency alignment

The unpublished v1.53.1 release candidate originally pinned the Alpine 3.24 OpenSSL CLI package at `3.5.7-r0`. Alpine rotated the repository to `3.5.8-r0` before publication, so protected Docker validation could no longer install the retired exact package. The release candidate now pins `3.5.8-r0` consistently in all four provider-App Dockerfiles, the regression contract and SPDX SBOM. This is release-engineering dependency maintenance only; private-PKI generation, certificate semantics and Gateway TLS policy are unchanged.

## Preserved contracts

- config-entry schema 12: unchanged
- portfolio payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 8 current; schemas 1–7 remain supported
- Historical compatibility remains intact: schemas 1–6 remain supported within that wider compatibility range
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged
- provider identity and one canonical snapshot per Gateway/provider: unchanged
- explicit operator acquisition switching and `fallback_policy: none`: unchanged
- independent holdings/cash evidence timestamps and configured freshness thresholds: unchanged
- verified private-PKI HTTPS, bearer authentication, DNS pinning and atomic source-set/LKG behavior: unchanged
- authenticated DKB FinTS acquisition remains disabled; the existing anonymous probe remains research-only/non-activatable and no authenticated probe is added
- This hotfix does not move PDF parsing into Portfolio Architect; Trade Republic statement parsing remains provider-local in its Gateway App
- no trading, order, transfer, payment, transaction-history, sell or withdrawal capability

No dashboard YAML replacement is required. The previously noted degraded-state dashboard redundancy and DKB probe timezone presentation remain presentation-only follow-up items and are not mixed into this correctness hotfix.

## Historical compatibility note

The former v1.19.0-rc2 brokerage probe remains historical only, is not present in the stable source tree, and is not promoted by this release.

The later v1.39 colourful allocation view was not included in v1.38.1; that historical sequencing remains unchanged.

The v1.33.0 source-freshness and plan-schedule separation remains anchored to the latest valid Portfolio Architect evaluation; v1.53.1 does not change any configured freshness threshold or recurring-plan schedule semantics.

No trading, order, transfer, payment, or transaction-history capability is introduced by this release; sell and withdrawal capability remain absent.
