# Portfolio Architect Gateway — DKB v1.62.5

Version 1.62.5 is a version-alignment release for this App. Supported CSV holdings/cash acquisition, private state, health schema 10, discovery transport, private-PKI/bearer boundary and no-fallback behavior are unchanged from v1.62.4; authenticated FinTS remains disabled.

Version 1.62.0 aligns this stable App with the additive common Gateway contracts used by Generic Import graduation: health schema 10 adds bounded `provider_name` while schemas 1–9 remain compatible. Supported CSV holdings/cash acquisition is unchanged; the anonymous FinTS probe remains experimental/research-only and authenticated FinTS remains disabled.

Private-PKI HTTPS, bearer authentication, provider identity, canonical evidence, `fallback_policy: none` and advisory-only semantics are unchanged.
