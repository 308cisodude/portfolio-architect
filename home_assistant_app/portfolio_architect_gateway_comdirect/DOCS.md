# Portfolio Architect Gateway — Comdirect v1.63.0

Version 1.63.0 is a package-alignment release for this App. Comdirect live API/CSV acquisition and explicit no-fallback authority, private state, health schema 10, discovery transport, verified private-PKI/bearer trust and `fallback_policy: none` are unchanged; the v1.63.0 work is confined to Portfolio Architect static reference-dashboard presentation and release tooling.

Version 1.62.0 aligns this stable App with the additive common Gateway contracts used by Generic Import graduation: health schema 10 adds bounded `provider_name` while schemas 1–9 remain compatible. Provider acquisition remains unchanged: explicit `live_api` or operator-selected complete `csv`, with no silent fallback.

Private-PKI HTTPS, bearer authentication, provider identity, canonical evidence, `fallback_policy: none` and advisory-only semantics are unchanged.
