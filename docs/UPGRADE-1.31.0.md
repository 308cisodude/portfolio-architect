# Upgrade to Portfolio Architect 1.31.0

Version 1.31.0 corrects the canonical Robotics target after v1.30 live acceptance showed
that the historically accepted distributing share class was still being presented as
the instrument to buy. The target is now the accumulating share class
`IE00BYZK4552` / `A2ANH0`. An existing `IE00BYWZ0333` / `A2ANH1` holding becomes
outside current plan scope and is not sold automatically.

## Recommended upgrade order

1. Update **Portfolio Architect through HACS to 1.31.0** and restart Home Assistant once.
2. Update installed official Gateway Apps to **1.31.0** in place for package alignment.
   Do not remove their App-private data. Provider acquisition, TLS trust and bearer
   tokens are unchanged by this release.
3. Confirm the existing Comdirect and Trade Republic sources remain healthy on verified
   HTTPS and DKB remains at its existing registration-gated state.
   Do not reauthenticate Comdirect solely because of this release when the current
   session is healthy.
4. Before editing the plan, check whether a Home Assistant **plan override** is enabled.
   A UI plan override supersedes `portfolio.yaml`; either update that override to the
   accumulating Robotics instrument or use **Reconfigure → Restore file-based plan**
   after the YAML files have been migrated.
5. Deliberately update the user-owned current-plan files from the v1.31 reference:
   - `portfolio.yaml`: make Robotics `IE00BYZK4552` / `A2ANH0`;
   - `instruments.yaml`: add/retain verified metadata for the accumulating target and
     retain the distributing instrument metadata while that holding exists;
   - `broker.yaml`: migrate to schema 2 only with fee/eligibility evidence you have
     independently verified; the reference adds an exact Trade Republic savings-plan
     route only for `IE00BYZK4552`;
   - `exceptions.yaml`: retain the old distributing-share-class decision as
     `status: superseded` rather than deleting its governance history.
6. Reload/restart Portfolio Architect so the new target/configuration fingerprint is
   evaluated.
7. No dashboard YAML migration is required for runtime correctness. If desired, replace
   or merge the v1.31 reference dashboard to surface the legacy distributing holding in
   the outside-current-plan section; HACS does not overwrite a user-owned dashboard.

## Expected state before the first accumulating purchase

With the former distributing Robotics shares still held and no accumulating Robotics
shares yet:

- active target positions: 7;
- active targets held: 6;
- missing active target: Robotics;
- the Robotics target is underweight and buy-enabled;
- the old distributing holding appears under **Outside current plan scope**;
- accepted active exceptions: 0;
- exception reviews required: 0; and
- no sell action is generated for the distributing holding.

That temporary six-of-seven coverage is intentional. It describes the desired active
architecture, not total economic similarity between share classes. Whole-portfolio
views continue to include the distributing holding.

After an accumulating Robotics holding is later acquired and imported, target coverage
can return to seven of seven while the distributing holding remains outside the plan
until the maintainer/user separately decides what to do with it.

## Fee-evidence freshness

Schema-2 execution evidence is deliberately time-bounded. The reference configuration
uses `fee_data_max_age_days: 30`; when evidence becomes stale, PA excludes that provider
route rather than silently assuming the old fee/eligibility is still current. Refresh
`source`/`as_of` only after re-verifying the relevant provider tariff and instrument
eligibility.

## DKB FinTS gate remains unchanged

The DKB FinTS research path is unchanged. The existing anonymous BPD probe still
requires Portfolio Architect's own product registration number. A positive `HIWPDS`
advertisement remains only bank-level capability evidence and does not yet enable live
holdings. Before any future DKB holdings implementation, an authenticated user
capability/UPD gate must independently confirm suitable read-only securities support.
No holdings request is added by v1.31.0.

## Preserved security boundary

This migration changes local target, policy and execution-evidence configuration only.
It does not add trading, automatic selling, order placement, transfers, payments,
transaction-history access, broker credentials, new Gateway endpoints, or broader
network permissions. Payload schema 8, REST portfolio schema 1 and Gateway health
schema 6 remain unchanged.
