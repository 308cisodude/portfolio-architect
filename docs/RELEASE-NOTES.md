# Portfolio Architect 1.48.1

Portfolio Architect v1.48.1 is a narrow Home Assistant-side freshness-policy correction prepared on top of the published v1.48.0 acquisition-mode release. It fixes the live-observed case where a deliberately static DKB CSV snapshot was still classified as a generic Gateway snapshot and therefore inherited the 24-hour live-source freshness window.

## Acquisition-aware freshness

Gateway health schema 7 already exposes bounded `acquisition_mode`. Portfolio Architect now uses that evidence when classifying both holdings and provider-scoped cash:

- `live_api` remains live evidence;
- `csv` is static CSV evidence;
- `pdf` is static imported-statement evidence; and
- an older/unknown Gateway without `acquisition_mode` keeps the conservative established provider fallback rather than being assumed static.

This applies consistently to the v1.48.0 Comdirect `live_api`/`csv` modes and to the existing DKB CSV and Trade Republic PDF acquisition paths. Static and live acquisition remain mutually exclusive where the provider Gateway defines them; this release does not add fallback between evidence families.

## Cadence-aware static defaults

Unconfigured evidence-kind defaults now reflect the operator burden and the plan cadence:

- live API / unknown Gateway evidence: **24 hours**;
- static CSV/PDF evidence for a **weekly** plan: **5 days / 120 hours**;
- static CSV/PDF evidence for a **monthly, quarterly or yearly** plan: **14 days / 336 hours**.

The monthly default deliberately permits roughly twice-monthly manual evidence refresh instead of requiring a new upload every week. Weekly plans retain a substantially tighter static window so the evidence is refreshed within approximately one execution period.

These are defaults only. Existing explicit `freshness_live_api_hours`, `freshness_statement_hours`, `freshness_csv_hours` and `freshness_other_hours` values remain authoritative and are not rewritten. A legacy pre-v1.33 installation that configured only the historical global freshness threshold likewise keeps that global value until the operator deliberately replaces it with evidence-kind values.

Holdings and cash keep independent evidence clocks. Refreshing one static evidence family never freshens another.

## Live regression reproduced

The v1.48.0 live upgrade exposed the exact regression fixture: DKB holdings generated at midnight were about 33.5 hours old and made the plan non-actionable even though the source was healthy and deliberately static. Under v1.48.1, health-schema-7 `acquisition_mode: csv` classifies that same evidence as CSV. With an unconfigured monthly policy it therefore uses 336 hours; an older DKB Gateway without an acquisition mode would still use the conservative 24-hour Gateway snapshot class.

## Historical compatibility contracts retained

The v1.33.0 source-freshness and plan-schedule separation remains anchored to the latest valid Portfolio Architect evaluation; v1.48.1 changes only unconfigured defaults and acquisition-mode classification and **does not change any configured freshness threshold**. The historical v1.19.0-rc2 brokerage-probe state remains historical and is not promoted by this release. The historical v1.39 colourful allocation view was not included in v1.38.1; that sequencing remains documented. Trade Republic provider-specific statement parsing remains in its Gateway; this release does not move PDF parsing into Portfolio Architect. authenticated DKB FinTS acquisition remains disabled. No trading, order, transfer, payment, or transaction-history capability is introduced.

## Preserved boundaries

- portfolio payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 7 current; schemas 1–6 remain supported;
- presentation schema 2 and broker schemas 1/2/3: unchanged;
- v1.48.0 Comdirect `live_api`/`csv` arbitration and no-fallback semantics: unchanged;
- DKB CSV and Trade Republic PDF provider acquisition/parsing: unchanged;
- source-set atomicity, Home Assistant LKG, planner economics, funding topology and execution-path behavior: unchanged;
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning and no-plaintext fallback: unchanged;
- No trading, order, transfer, payment, or transaction-history capability is added; sell and withdrawal capability remain absent; and
- no dashboard YAML replacement is required.
