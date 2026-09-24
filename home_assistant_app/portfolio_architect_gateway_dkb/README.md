## v1.65.0

After a successful user-initiated read-only HKWPD observation, admin Ingress temporarily displays independent DKB CSV and FinTS cards with normalized ISIN, quantity, value, currency and source timing. A bounded bank instrument field and total-value currency code are captured before PyFinTS discards them; the library's unit-price currency is labeled separately. Only an explicit `ISIN` marker supplies a missing parser ISIN, and conflicting identifiers suppress normalization. The shadow detail and its completeness count are available in App memory for five minutes. Approval and expiry are shown on the page. No automatic equivalence judgment, credential storage, background refresh or acquisition switch occurs. The CSV export has a date only.

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
