# Upgrade to Portfolio Architect v1.62.2

v1.62.2 is a narrow follow-up to v1.62.1. It preserves the integration-owned first-run architecture and fixes the live-observed Home Assistant frontend behavior that could render selector minima or first options as apparently preselected values in the initial-plan wizard.

## Why this patch exists

Clean-room acceptance of v1.62.1 proved the intended lifecycle:

1. Portfolio Architect is initialized first and owns its singleton service/configuration directory.
2. The empty service is `source_required` and creates no plan files.
3. A ready Gateway becomes a candidate for the existing service rather than creating another Portfolio Architect entry.
4. After the first validated source is attached, the service becomes `plan_required`.

When **Complete initial setup** was opened live, Home Assistant rendered the first target instrument selected and numeric selector minima such as `0.01` even though Portfolio Architect had supplied no suggested values. Those frontend artifacts must not become investment assumptions.

## Corrected first-run wizard

v1.62.2 deliberately renders first-run fields without required-selector defaults and validates required presence on submission instead.

Expected initial state:

- Plan name: blank
- Monthly contribution: blank
- Target instruments: none selected
- Allocation corridor: blank
- Minimum purchase: blank
- Purchase rounding step: blank

Subsequent instrument and policy pages follow the same rule. Numeric values and enumerations begin blank. Yes/No decisions use an explicit three-state-safe selector whose initial state is unanswered. Submission fails closed until the user has made every required choice.

The final candidate is still calculated before installation. Existing configuration is never overwritten and no execution provider/funding route is created automatically.

## Generic Import colour contract

Generic Import now renders a source profile amber while setup is incomplete and blue once its first validated holdings snapshot makes it READY. The CSV method remains green because it is the profile's active and authoritative acquisition method. This does not add an adoption-status API or Home Assistant permission; the profile card represents source readiness, not knowledge of PA-side adoption.

## Existing v1.62.1 installations

A v1.62.1 entry in `source_required` or `plan_required` remains in that state across the update. Existing ready Generic profiles, provider IDs, mappings, snapshots, evidence timestamps, private CA and bearer material remain unchanged. Do not recreate the PA service or Generic profile solely for this patch.

Already configured installations migrate/load unchanged under config-entry schema 13. No source migration, broker migration, Gateway reauthentication or dashboard replacement is required.

All four active Gateway App packages are aligned to v1.62.2. Comdirect, DKB and Trade Republic runtime behavior is unchanged; Generic Import has only the READY-profile presentation adjustment described above.

## Planned live acceptance

On the existing LG clean-room fixture:

1. Update Portfolio Architect and Generic Import to v1.62.2; preserve the initialized PA entry and ready `Test Broker` profile.
2. Confirm PA still has exactly one service and the existing Generic provider identity is unchanged.
3. Open **Complete initial setup** and verify no target, number, enumeration or Yes/No decision is preselected.
4. Submit with missing fields and verify field-level rejection with no YAML files created.
5. Enter explicit synthetic choices through all pages and confirm the candidate validates before the four configuration files are installed.
6. Confirm the entry reloads into normal configured runtime only after successful completion.
7. Confirm the Generic READY profile card is blue while its active/authoritative CSV acquisition presentation remains green.

On the established production installation, update only after clean-room acceptance; existing source/freshness/planner economics must remain unchanged.
