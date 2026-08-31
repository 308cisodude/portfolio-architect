# Portfolio Architect Gateway — Comdirect v1.62.0

Version 1.62.0 aligns this stable App with the additive common Gateway contracts used by Generic Import graduation: health schema 10 adds bounded `provider_name` while schemas 1–9 remain compatible. Provider acquisition remains unchanged: explicit `live_api` or operator-selected complete `csv`, with no silent fallback.

Private-PKI HTTPS, bearer authentication, provider identity, canonical evidence, `fallback_policy: none` and advisory-only semantics are unchanged.
