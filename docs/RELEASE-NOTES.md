# Portfolio Architect 1.51.0

Portfolio Architect v1.51.0 completes the current provider-acquisition cleanup. The Home Assistant integration no longer parses or acquires any provider-neutral mapped CSV itself. That explicit escape hatch now lives in a fourth isolated App, **Portfolio Architect Gateway — Generic Import**, which exposes the same canonical read-only REST snapshot contract as the official provider Apps.

## Generic Import Gateway

The new App has fixed provider identity `generic_csv` and acquisition mode `csv`. It accepts one explicitly mapped CSV through admin-only Ingress, with bounded encoding, delimiter, header-row, decimal-format and column mapping. Raw uploaded bytes are transient. Only the validated canonical holdings snapshot, bounded mapping configuration and privacy-safe import outcome are persisted. It does not import provider cash, perform currency conversion, accept provider credentials or expose any transaction capability.

Successful import time is the evidence timestamp because the generic format has no standardized institution-issued portfolio timestamp. Re-import is therefore an explicit operator action that refreshes the static evidence clock.

Config-entry schema 12 fails closed if an older installation still actively uses the Home Assistant-side local generic CSV source. Such an installation must remain on v1.50.0, import into the Generic Import Gateway, explicitly reconfigure Portfolio Architect to that verified REST source, verify it, and then upgrade.

## DKB probe timestamp display

The DKB App continues to persist `probe_sent_at` as timezone-aware UTC immediately before the explicit anonymous BPD network request and exposes that exact value through `/status`. The Ingress UI no longer assumes `Europe/Berlin`. Because the supported Ingress request contract does not provide the App with the viewing Home Assistant user's frontend timezone, v1.51.0 uses browser `Intl.DateTimeFormat` as a conservative local-display fallback and continues to show authoritative UTC alongside it. No undocumented parent-frontend access or Home Assistant API permission is introduced.

## Preserved architecture

Comdirect `live_api`/`csv` arbitration, DKB CSV holdings/cash evidence, Trade Republic statement acquisition, v1.48 cadence-aware freshness, independent holdings/cash clocks, provider-scoped cash, funding topology, planner economics, private-PKI transport, DNS pinning, configured-source atomicity and Home Assistant LKG all remain unchanged. Trade Republic provider-specific statement parsing remains in its Gateway; this release does not move PDF parsing into Portfolio Architect.

The integration retains exactly one config entry with one primary REST Gateway plus optional validated supplemental REST Gateways. Generic Import is just another isolated canonical snapshot producer when deliberately configured.

The historical v1.19.0-rc2 brokerage-probe state remains historical and is not promoted by this release.

The v1.33.0 source-freshness and plan-schedule separation remains anchored to the latest valid Portfolio Architect evaluation; v1.51.0 does not change any configured freshness threshold. The historical v1.39 colourful allocation view was not included in v1.38.1; that sequencing remains documented.

Compatibility remains explicit:

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 7 current; schemas 1–6 remain supported
- presentation schema 2: unchanged
- broker schemas 1/2/3: unchanged

No trading, order, transfer, payment, or transaction-history capability is introduced; sell and withdrawal capability remain absent. authenticated DKB FinTS acquisition remains disabled.
