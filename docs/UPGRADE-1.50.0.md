# Upgrade to Portfolio Architect 1.50.0

Version 1.50.0 makes Portfolio source management explicitly reflect the existing architecture: one primary REST Gateway plus optional provider-isolated supplemental REST Gateways. It also adds a persisted server-side dispatch timestamp to the anonymous DKB FinTS research probe.

## Normal upgrade from v1.49.0

1. Update the Portfolio Architect integration to **1.50.0** and restart Home Assistant once.
2. Align the Comdirect, DKB and Trade Republic Gateway Apps to **1.50.0** in place. Preserve all App-private state and trust material.
3. Open **Settings → Devices & services → Portfolio Architect → Configure → Portfolio sources**. Confirm the menu now shows **Primary REST Gateway** separately from **Additional REST Gateways**.
4. Open **Primary REST Gateway** and confirm the visible provider/endpoint context matches the existing primary source. Saving unchanged values is optional; no source migration is required.
5. Open **Additional REST Gateways** and confirm Add/Edit/Remove actions are available for the existing supplemental providers. Do not remove or recreate a source solely for upgrade acceptance.
6. Open the DKB Gateway Ingress page. Existing anonymous BPD results remain readable. The new **Last probe sent** field initially reports no v1.50 dispatch timestamp until a new probe is deliberately sent.
7. No dashboard YAML replacement, provider reauthentication, CSV/PDF re-import or broker migration is required solely because of this release.

## Source-management semantics

The primary source remains structurally distinct from supplemental Gateways. Editing the primary REST transport never converts it into a supplement and there is no Remove-primary action. If its endpoint is changed, Portfolio Architect requires verified HTTPS and validates that the new endpoint still exposes the same provider identity plus a matching healthy snapshot before saving.

Supplemental REST Gateways now have coherent Add/Edit/Remove flows. Editing one keeps its stored provider identity immutable, rejects duplicate primary/supplemental endpoints or providers, and requires verified-HTTPS health plus exact snapshot-integrity agreement before saving. Existing private-CA trust is retained automatically when an endpoint is unchanged.

The single config-entry architecture, configured-source atomicity and Home Assistant LKG binding are unchanged.

## DKB probe timestamp

The DKB App now persists a separate UTC timestamp immediately before dispatching an operator-requested anonymous BPD probe. The Ingress UI displays the timestamp in the DKB-local Europe/Berlin time and also shows the authoritative UTC value. The `/status` document exposes the same bounded `probe_sent_at` value.

Changing the configured FinTS product registration clears both the previous capability result and its dispatch timestamp, so evidence from one registration identity is never presented as belonging to another.

The timestamp is observability only. The probe request, endpoint, bounded response parsing, response fingerprints and registration gate are unchanged. Authenticated DKB FinTS acquisition remains disabled.

## Preserved boundaries

- portfolio payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 7: unchanged; schemas 1–6 remain supported
- presentation schema 2 and broker schemas 1/2/3: unchanged
- Comdirect `live_api`/`csv` arbitration and no-fallback semantics: unchanged
- DKB CSV and Trade Republic PDF acquisition/parsing: unchanged
- v1.48 acquisition-aware freshness and explicit thresholds: unchanged
- verified private-PKI HTTPS, bearer authentication, DNS pinning, source-set atomicity and Home Assistant LKG: unchanged
- no trading, order, transfer, payment, transaction-history, sell or withdrawal capability is added
