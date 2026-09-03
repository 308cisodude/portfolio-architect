# Portfolio Architect Gateway runtime v1.62.2

Version 1.62.2 is a release-alignment update for the common Gateway runtime. Gateway acquisition, health schema 10, REST portfolio schema 1, provider identity, discovery transport and private-PKI behavior remain unchanged; the first-run explicit-choice fix is owned by the Home Assistant integration. Generic Import adds only a source-profile readiness colour presentation adjustment.

Version 1.62.0 adds backward-compatible Gateway health schema 10 with a bounded human-readable `provider_name` while retaining schemas 1–9, REST portfolio schema 1, provider identity, acquisition authority, canonical evidence clocks, private-PKI transport and `fallback_policy: none`. The common Supervisor-discovery publisher also supports transport schema 2 for an exact provider-specific REST path and provider display name; fixed native-provider Apps continue to use the established schema-1 discovery shape.

The common runtime remains provider-neutral and read-only. Generic Import uses these additive contracts to expose multiple isolated logical providers from one trusted App origin; native Comdirect, DKB and Trade Republic acquisition behavior is unchanged.
