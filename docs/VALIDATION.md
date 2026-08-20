# v1.36.1 validation

Portfolio Architect v1.36.1 is prepared from the exact published v1.36.0 tracked-source baseline after live acceptance isolated one frontend composition defect: presentation-slot entities and filters were correct, but `entity-filter` did not produce a populated nested Distribution card. The hotfix is deliberately dashboard/presentation-only apart from normal release version alignment.

Release-specific validation must prove:

- no Distribution card remains in the canonical reference dashboard;
- the EN/DE whole-portfolio, current-plan and target-plan allocation filters feed native Entities child cards with `show_header_toggle: false`, `show_empty: false` and the established positive numeric filter;
- dynamic candidate ranges remain 32 targets, 512 outside holdings and 256 policy findings;
- all dynamic presentation candidates request structured entity-only Home Assistant names while conditioned allocation rows retain their per-entity state conditions;
- no opaque target IDs, accepted holding IDs or sample-instrument names are reintroduced into dashboard inventory;
- presentation schema 2 and the v1.36.0 slot backend remain unchanged;
- English and German views use the same dynamic entity inventory and all tracked dashboard YAML remains parseable;
- payload schema 8, REST portfolio schema 1, Gateway health schema 6, broker schemas 1/2/3, provider cash/funding, Comdirect v1.35.4 input normalization, provider acquisition and private-PKI security contracts remain unchanged;
- the shared human-input validation helper remains deferred and is not introduced by this hotfix;
- all integration/Gateway package version markers align to 1.36.1;
- publication/privacy, deterministic release, archive integrity and immutable workflow contracts remain green.

Local Docker availability is not assumed; protected GitHub **Validate release** remains authoritative for provider-App Docker/Supervisor/private-PKI smoke execution.
