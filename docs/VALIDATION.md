# v1.38.0 validation

Portfolio Architect v1.38.0 is prepared from the exact published and live-accepted v1.37.0 tracked-source baseline. The release is a Home Assistant-native dashboard usability milestone: it restores copy-friendly ISIN access for dynamic recommended purchases and adds policy-aware investment-cash context without changing provider runtime or Gateway wire contracts.

## Required evidence

Release-specific validation must prove:

- all integration/common Gateway/provider App version markers align to 1.38.0;
- dynamic recommended-purchase rows remain bounded generic presentation-slot candidates with no hard-coded instrument inventory;
- tapping a recommended-purchase row opens the same slot's ISIN entity and holding it opens the same slot's purchase explanation;
- only positive proposed-buy rows remain visible;
- **Authorized investment cash** exposes total available cash plus cash actually excluded by policy;
- **Cash after recommended purchases** exposes the same context plus planned cash outlay;
- complete provider-scoped eligible/authorized evidence aggregates deterministically, while incomplete provider-scoped evidence omits context rather than falling back to a misleading partial total;
- English and German dashboard views expose the same underlying dynamic inventory with locale-appropriate cash-context formatting;
- the v1.37 shared human-input helper and Comdirect cash-policy behavior remain unchanged;
- common Gateway and Comdirect App source mirrors remain byte-identical for `app.py`, `cash_policy.py`, `human_input.py` and `transport.py`;
- all established publication/privacy, provider, presentation, wire-schema, private-PKI and advisory/no-trading regressions remain green.

The complete release gate remains `tools/release_check.sh`. Local preparation environments without Docker must run every available constituent phase independently; the protected GitHub **Validate release** workflow remains authoritative for provider-App Docker/Supervisor/private-PKI smoke execution.
