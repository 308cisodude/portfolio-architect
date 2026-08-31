# Upgrade to Portfolio Architect v1.61.2

v1.61.2 is a narrow Home Assistant-side hotfix for the **Primary REST Gateway identity context** exposed during v1.61.1 live acceptance. It does not change provider acquisition, Gateway runtime, wire schemas, planner economics, dashboard YAML, the v1.61.1 provider-neutral discovery lifecycle, or the authenticated-DKB-FinTS research gate.

## What changes

The native **Configure → Portfolio sources → Primary REST Gateway** form now remains self-identifying when a one-off fresh health request fails but the running Portfolio Architect coordinator still carries an already-validated primary Gateway identity. In that case the immutable provider context is displayed from runtime state instead of degrading to `Unknown`.

Display fallback does not weaken mutation validation. When the operator changes the primary endpoint, Portfolio Architect still requires a successful fresh read of the current primary identity and full verified-HTTPS, exact-provider, health and live snapshot-integrity validation of the candidate before saving. A transient failure of the current fresh identity lookup therefore leaves the existing source unchanged.

## Preserved v1.61.1 discovery behavior

- A fresh installation may bootstrap the singleton PA config entry from any validated Portfolio Architect Gateway; Comdirect is not required.
- Concurrent first-run discoveries share the singleton integration unique ID and collapse to one visible initial Add flow while other provider discoveries remain candidates.
- Once the canonical PA entry exists, an unconfigured provider does not create another top-level Portfolio Architect Add card.
- Discovered candidates remain available only below **Configure → Portfolio sources → Additional REST Gateways → Add discovered REST Gateway** and explicit adoption still requires the App-private bearer token plus verified HTTPS, exact provider identity, healthy Gateway state and snapshot timestamp/count/SHA-256 integrity validation.
- Comdirect may be supplemental when another provider is primary.

## Compatibility and security boundary

Health schema 9 and schemas 1–8 compatibility, REST portfolio schema 1, Portfolio payload schema 8, config-entry schema 12, canonical evidence clocks, evidence-kind freshness, `fallback_policy: none`, LKG/anti-rollback/source-set atomicity, private-PKI HTTPS, bearer authentication, DNS pinning, planner economics, funding topology and advisory-only semantics are unchanged. Authenticated DKB FinTS remains disabled/research-only. There is **no silent fallback** between acquisition methods and no trading, order, transfer, payment, transaction-history, sell or withdrawal capability. The historical **Comdirect LEGACY** App remains removed from the active repository.

## Generic Import isolation

If Generic Import is installed only for a standalone smoke or experiment, do **not** adopt it as a real production Portfolio Architect source. The isolated smoke test must not alter the real source set; the temporary Generic Import App should be uninstalled after this standalone smoke test unless it is intentionally being adopted.

## Upgrade

1. Update the Portfolio Architect HACS integration to v1.61.2 and perform the normal Home Assistant restart.
2. Align installed official Gateway Apps to v1.61.2 for release-version consistency. Their runtime/acquisition behavior is unchanged from v1.61.1.
3. No dashboard YAML replacement is required.
4. Existing source endpoints, private CA trust, bearer tokens, acquisition methods, evidence clocks, plan/broker configuration and funding topology remain unchanged.

## Live acceptance

1. Confirm Portfolio Architect returns healthy with the same configured provider/source set and no new top-level Portfolio Architect discovery card.
2. Open **Configure → Portfolio sources → Primary REST Gateway**. The immutable provider label must identify the current primary provider rather than `Unknown` even if a transient standalone health request occurs while the coordinator retains validated identity.
3. Do not change the endpoint merely to test failure behavior in production. The endpoint-change fail-closed boundary is executable-regression covered.
4. Confirm **Additional REST Gateways → Add discovered REST Gateway** still contains only genuine unconfigured Supervisor-discovered candidates and that configured providers do not reappear there.
5. Complete the non-destructive v1.61.0 removal-confirmation acceptance by entering each confirmation form and backing out without enabling **Confirm removal**.
6. Confirm planner/source/freshness outputs remain unchanged.
