# Upgrade to Portfolio Architect 1.36.1

Version 1.36.1 is a narrow presentation hotfix for installations already on v1.36.0. It fixes the live-observed empty dynamic allocation cards and shortens dynamic instrument labels without changing provider runtime, portfolio calculations or Gateway wire/security contracts.

## Upgrade

1. Update Portfolio Architect through HACS to 1.36.1 and restart Home Assistant once.
2. Confirm the existing provider/cash/funding state remains healthy. No Comdirect reauthentication, cash-policy change, Trade Republic statement re-import or DKB probe is required.
3. Align the Comdirect, Trade Republic and DKB Gateway Apps to 1.36.1 in place. Their provider behavior is unchanged.
4. Deliberately bulk-replace the copied Portfolio Architect Lovelace YAML with the supplied `portfolio-architect-v1.36.1-bilingual-dashboard.yaml`; HACS does not overwrite user-owned dashboard YAML.
5. Confirm the three allocation surfaces now show filtered numeric entity rows rather than the empty Distribution-card placeholder.
6. Confirm target, outside-scope and policy inventories still reconcile with their aggregate counts, EN/DE expose the same inventory, compact labels omit the Portfolio Architect device prefix, and no unavailable trailing slots are shown.
7. Confirm Source healthy / Gateway status OK / Operating mode Live remain unchanged for live providers. DKB remains deliberately manual-only/non-live.

The v1.36.0 presentation-slot backend and presentation schema 2 are intentionally unchanged. The broader shared human-input validation helper also remains deferred; the working v1.35.4 Comdirect cash-input parser is preserved as-is.
