# Upgrade to Portfolio Architect 1.37.0

Version 1.37.0 introduces shared bounded human-numeric validation in the Gateway runtime and migrates the existing Comdirect cash-policy amount fields onto the shared EUR primitive without changing their accepted syntax or policy semantics.

## Upgrade

1. Update Portfolio Architect through HACS to 1.37.0 and restart Home Assistant once.
2. Confirm the existing provider/cash/funding state remains healthy. No dashboard replacement, Comdirect reauthentication, cash-policy change, Trade Republic statement re-import or DKB probe is required.
3. Align the Comdirect, Trade Republic and DKB Gateway Apps to 1.37.0 in place. The shared helper is packaged consistently across the provider Apps, but only the existing Comdirect cash-policy amount fields consume it in this release.
4. Confirm Source healthy / Gateway status OK / Operating mode Live remain unchanged for live providers. DKB remains deliberately manual-only/non-live.
5. Optional focused live check: reopen **Investment cash authorization** and confirm the existing retained/capped amount is still canonical. If desired, submit one already-proven locale form such as `1024,00` and verify the policy round-trips without changing its mathematics.

## Compatibility and scope

The existing v1.35.4 cash-input contract is preserved: common decimal comma/dot and validated dot/comma/space/apostrophe grouping remain accepted, invalid input remains bounded and the previous valid private state is preserved.

No dashboard YAML migration is required. Presentation schema 2, REST portfolio schema 1, Gateway health schema 6, broker schemas 1/2/3, provider acquisition, private-PKI transport, funding/cash mathematics and the advisory/no-trading boundary are unchanged.

The shared parser is deliberately opt-in. Protocol identifiers, registrations, credentials, tokens and exact IDs remain on provider/field-specific validation paths and are not locale-normalized.
