# v1.34.1 validation

Portfolio Architect v1.34.1 is a presentation-correctness hotfix prepared from the exact
live-accepted v1.34.0 tracked-source baseline.

The release must prove:

- integration, engine, common Gateway and all three official App versions align at `1.34.1`;
- every configured target receives the established whole-portfolio allocation entity from target
  state, including a missing target at exactly `0%`;
- held-target allocation entity IDs/unique IDs remain unchanged from v1.34.0 and no duplicate
  holding allocation entity is created for the same current-plan target;
- outside-current-plan allocation entities remain evidence-driven;
- all reference-dashboard outside-scope distribution bindings use current ISIN-first holding IDs
  rather than obsolete WKN-era IDs;
- the hard-coded outside-scope detail Tile inventory remains intentionally unchanged;
- the v1.34 presentation model remains the complete dynamic current-state inventory;
- opaque target IDs, schema-1 compatibility, portfolio calculations, freshness, scheduling,
  provider acquisition/diagnostics, authorized-cash and execution behavior remain unchanged;
- payload schema 8, REST portfolio schema 1 and Gateway health schema 6 remain unchanged; and
- no trading, order placement, automatic sell, transfer, payment or transaction-history
  capability is introduced.

Run the complete regression suite, `git diff --check`, Python compilation, structured-file
parsing, strict publication/privacy checks, three independent reproducible release builds,
release verification, release-artifact privacy validation and independent Git-overlay/binary-
patch replay over the exact v1.34.0 tracked baseline.

Protected GitHub workflows remain authoritative for actual provider-App Docker/private-PKI smoke
execution because Docker is unavailable in the preparation environment.

## Live acceptance

1. Update Portfolio Architect to 1.34.1 and restart Home Assistant; keep the schema-2 plan, source
   configuration, schedule, freshness policy and broker configuration unchanged.
2. Confirm the whole-portfolio distribution shows the missing accumulating Robotics target by its
   friendly name at `0%`, not as an unresolved entity ID.
3. Replace/update the copied reference dashboard with the v1.34.1 dashboard and confirm every
   currently referenced outside-scope distribution item has a real percentage rather than
   `Unavailable`.
4. Confirm 6/7 target coverage, three healthy providers, source freshness, 7-Sep/5-Oct schedule
   and the presentation-model outside-scope inventory remain unchanged.
5. Align all three Gateway Apps to 1.34.1 in place; no Comdirect reauthentication, Trade Republic
   re-import or DKB reprobe is required.
