# v1.36.0 validation

Portfolio Architect v1.36.0 is prepared from the exact published/live-accepted v1.35.4 source baseline. It completes the Home Assistant-native dynamic portfolio-presentation milestone without changing provider acquisition, execution/funding mathematics or Gateway wire/security contracts.

Release-specific validation must prove:

- presentation schema 2 preserves stable target-ID/position-ID identity while adding bounded one-based slot metadata;
- target, outside-scope and active-policy slot order comes from the same validated current-state collections used by the presentation model;
- slot aliases are diagnostic UI projections, expose the underlying stable identity and do not claim measurement state classes/history identity;
- the reference dashboard contains no instrument-specific opaque target IDs or holding position IDs;
- the dashboard enumerates the complete accepted backend bounds of 32 target, 512 outside-holding and 256 policy candidates;
- only Home Assistant core cards are used (`entity-filter`, Entities, Glance, Distribution, Tile, Conditional and headings); no `auto-entities`, card-mod, custom JavaScript or custom cards are introduced;
- English and German views use the same entity inventory and remain parseable native Sections views;
- user-owned dashboard copies remain opt-in and are never overwritten by HACS/integration updates;
- payload schema 8, REST portfolio schema 1, Gateway health schema 6, broker schemas 1/2/3, v1.35 cash/funding behavior, v1.35.1 Comdirect resilience and v1.35.4 cash-input normalization remain unchanged;
- all three provider Apps are package/version-aligned to 1.36.0 without provider-runtime semantic changes;
- publication/privacy, reproducible release, ZIP safety and immutable workflow contracts remain green.

Local Docker availability is not assumed; protected GitHub **Validate release** remains authoritative for provider-App Docker/private-PKI smoke execution.
