## v1.64.4

After a successful read-only HKWPD observation, admin Ingress temporarily displays separate DKB CSV and FinTS tables with ISIN, quantity, value, currency availability and source timing. This is a five-minute in-memory view for human review; no automatic equivalence judgment or acquisition switch occurs. The CSV export has a date only, and PyFinTS does not expose the currency for its total holding value.

## v1.64.3

The read-only HKWPD probe now supplies DKB's verified BIC to PyFinTS when converting its one UPD-authorized depot. This corrects the local `TypeError` observed in v1.64.2. The BIC is used for library account conversion; account identifiers and holdings stay transient.

## v1.64.2

Failed read-only research observations now report a fixed failure stage and error category. An eligible-depot count is shown as not determined when account discovery did not finish. Bank response text, exception messages, identifiers and positions are not retained.

## v1.64.1

Admin Ingress can make a one-shot read-only FinTS holdings research request for one authorized depot. Only a bounded count and outcome persist; DKB CSV remains authoritative. Use the banking Anmeldename and password, not the product registration number or DKB app PIN.

## v1.64.0

One-shot authenticated DKB UPD capability observation is available in admin Ingress. It never changes CSV acquisition.

# Portfolio Architect Gateway — DKB v1.63.0

Version 1.63.0 is a package-alignment release for this App. DKB CSV holdings/cash acquisition and research-only anonymous FinTS probing, private state, health schema 10, discovery transport, verified private-PKI/bearer trust and `fallback_policy: none` are unchanged; the v1.63.0 work is confined to Portfolio Architect static reference-dashboard presentation and release tooling.

Version 1.62.0 aligns this stable App with the additive common Gateway contracts used by Generic Import graduation: health schema 10 adds bounded `provider_name` while schemas 1–9 remain compatible. Supported CSV holdings/cash acquisition is unchanged; the anonymous FinTS probe remains experimental/research-only and authenticated FinTS remains disabled.

Private-PKI HTTPS, bearer authentication, provider identity, canonical evidence, `fallback_policy: none` and advisory-only semantics are unchanged.
