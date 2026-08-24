# Portfolio Architect 1.50.0

Portfolio Architect v1.50.0 is the source-architecture UX milestone after the live-accepted v1.49.0 provider-acquisition cleanup. It does not change portfolio acquisition or planning mathematics. Instead, Configure now presents the source model the way the runtime has worked since multi-Gateway support: exactly one primary REST Gateway, plus optional provider-isolated supplemental Gateways.

## Explicit primary-source model

**Configure → Portfolio sources** now separates **Primary REST Gateway** from **Additional REST Gateways**. The primary editor shows immutable provider/endpoint context and permits only transport/authentication changes. A changed endpoint must use verified HTTPS, must remain the same provider identity, must not collide with any supplement, and must expose a healthy snapshot whose timestamp, position count and SHA-256 integrity metadata agree with health before the config entry is updated.

There is deliberately no Remove-primary action. The single-entry architecture and primary/supplemental distinction remain structural rather than merely visual.

## Coherent supplemental Add/Edit/Remove

Additional REST Gateways now expose native **Add**, **Edit** and **Remove** actions. Editing a supplement keeps its provider ID immutable, retains existing private-CA trust when its endpoint is unchanged, rejects endpoint/provider collisions, and performs the same verified-HTTPS health and snapshot-integrity checks used when a source is first added.

No source is silently added, replaced, removed or reclassified.

## DKB probe observability

The DKB anonymous FinTS BPD research UI now records and persists **Last probe sent** immediately before each explicit probe attempt. The UI renders the server-side timestamp in DKB-local Europe/Berlin time and includes the authoritative UTC timestamp; the bounded `/status` document exposes `probe_sent_at` as well.

This solves the operational ambiguity of two cryptographically identical DKB rejection responses: an operator can now prove that a new probe was actually initiated even when every response fingerprint and bank return message remains unchanged. Changing the FinTS product registration clears both old probe evidence and its dispatch timestamp.

The probe itself is unchanged. It remains anonymous, registration-gated, read-only capability research. No DKB login, PIN/TAN, authenticated holdings/balance/transaction request, order, transfer, payment, sell or withdrawal capability is introduced.

## Preserved architecture

Comdirect `live_api`/`csv` arbitration, DKB CSV holdings/cash evidence, Trade Republic statement acquisition, v1.48 cadence-aware freshness, independent holdings/cash clocks, provider-scoped cash, funding topology, planner economics, private-PKI transport, DNS pinning, configured-source atomicity and Home Assistant LKG all remain unchanged.

The provider-neutral mapped generic CSV adapter remains inside Portfolio Architect for now. A deliberate generic Import Gateway remains the later source-architecture milestone.

No dashboard YAML replacement is required.

Compatibility remains explicit:

- portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 7 current; schemas 1–6 remain supported;
- presentation schema 2 and broker schemas 1/2/3: unchanged.

The v1.33.0 source-freshness and plan-schedule separation remains anchored to the latest valid Portfolio Architect evaluation; v1.50.0 does not change any configured freshness threshold. The historical v1.39 colourful allocation view was not included in v1.38.1; that sequencing remains documented. The historical v1.19.0-rc2 brokerage-probe state remains historical and is not promoted by this release. No trading, order, transfer, payment, or transaction-history capability is introduced; sell and withdrawal capability remain absent as well.

authenticated DKB FinTS acquisition remains disabled; the anonymous BPD probe remains a separate research gate.

Trade Republic provider-specific statement parsing remains in its Gateway; this release does not move PDF parsing into Portfolio Architect.
