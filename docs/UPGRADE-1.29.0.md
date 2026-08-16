# Upgrade to Portfolio Architect 1.29.0

Version 1.29.0 changes **reference-dashboard presentation only** apart from normal
version/package metadata. Provider acquisition, calculations, entities, Gateway
runtime, private-PKI verified HTTPS and the v1.28 DKB FinTS gate are unchanged.

## Runtime upgrade

1. Update **Portfolio Architect** through HACS to 1.29.0.
2. Restart Home Assistant once and confirm the Portfolio Architect version entity
   reports `1.29.0`.
3. Update installed provider Gateway Apps to 1.29.0 in place for version alignment.
4. Preserve all App-private data. Do not remove/reinstall an App or regenerate a
   bearer token or CA. Do not reauthenticate Comdirect solely because of this release.
5. Confirm configured Comdirect and Trade Republic sources remain healthy and their
   verified-HTTPS CA fingerprints are unchanged.
6. If the DKB App is installed, confirm its FinTS capability-probe state remains
   `registration_required` until Portfolio Architect receives its own registration
   number.

The v1.28 DKB research gate is unchanged and does not yet enable live DKB holdings:
a later anonymous BPD result advertising
`HIWPDS` would remain bank-level capability evidence only. Live holdings still require
a separate authenticated user-capability/UPD validation and safe DKB-App decoupled
authentication design before any acquisition path may be enabled.

## Reference-dashboard update

No dashboard YAML migration is required for runtime compatibility. HACS does **not**
overwrite a dashboard that you previously imported or copied, however. To see the
v1.29.0 visual polish, deliberately update your dashboard from
`portfolio-architect-v1.29.0-bilingual-dashboard.yaml`, or merge the policy-section
change below into your existing customized dashboard.

The only intended policy-layout addition is a conditional native subtitle immediately
before the four fee-opportunity tiles:

```yaml
- type: conditional
  conditions:
  - condition: numeric_state
    entity: sensor.portfolio_architect_optimisation_opportunity_count
    above: 0
  card:
    type: heading
    heading: Optimisation opportunities
    heading_style: subtitle
    icon: mdi:lightbulb-on-outline
    badges:
    - type: entity
      entity: sensor.portfolio_architect_optimisation_opportunity_count
      show_icon: false
      show_state: true
      tap_action:
        action: more-info
  grid_options:
    columns: full
    rows: auto
```

The German reference uses `Optimierungsmöglichkeiten` for the heading. Everything
else is identical.

The green mandatory-controls tile, exception count, Robotics exception, decision and
review tiles, and all four blue opportunity tiles remain unchanged.

## Expected live appearance

With one accepted exception and four fee opportunities, the policy section should
read visually as:

1. mandatory controls compliant;
2. accepted exception and its decision/review lifecycle;
3. **Optimisation opportunities** with count `4`;
4. the four blue fee-opportunity tiles.

If the opportunity count becomes zero, both the subtitle and its count badge should
be absent.

No entity migration or configuration-entry migration is required.
