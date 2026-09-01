# Portfolio Architect Gateway — Comdirect v1.62.1

Version 1.62.1 is a version-alignment release for this App. Its provider acquisition, private state, health schema 10, discovery transport, private-PKI/bearer boundary and no-fallback behavior are unchanged from v1.62.0; first-run Portfolio Architect initialization is integration-owned.

Version 1.62.0 aligns this stable App with the additive common Gateway contracts used by Generic Import graduation: health schema 10 adds bounded `provider_name` while schemas 1–9 remain compatible. Provider acquisition remains unchanged: explicit `live_api` or operator-selected complete `csv`, with no silent fallback.

Private-PKI HTTPS, bearer authentication, provider identity, canonical evidence, `fallback_policy: none` and advisory-only semantics are unchanged.
