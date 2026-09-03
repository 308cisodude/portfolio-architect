# Portfolio Architect Gateway runtime v1.62.3

Version 1.62.3 aligns the common Gateway runtime with the Trade Republic cash-statement compatibility hotfix. Common Gateway acquisition, health schema 10, REST portfolio schema 1, provider identity, discovery transport and private-PKI behavior remain unchanged; only the Trade Republic provider package changes parsing behavior.

Version 1.62.0 adds backward-compatible Gateway health schema 10 with a bounded human-readable `provider_name` while retaining schemas 1–9, REST portfolio schema 1, provider identity, acquisition authority, canonical evidence clocks, private-PKI transport and `fallback_policy: none`. The common Supervisor-discovery publisher also supports transport schema 2 for an exact provider-specific REST path and provider display name; fixed native-provider Apps continue to use the established schema-1 discovery shape.

The common runtime remains provider-neutral and read-only. Generic Import uses these additive contracts to expose multiple isolated logical providers from one trusted App origin; native Comdirect, DKB and Trade Republic acquisition behavior is unchanged.
