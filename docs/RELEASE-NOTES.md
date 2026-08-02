# Portfolio Architect 1.17.2

Version 1.17.2 repairs the HACS release-asset layout defect in v1.17.1. The
v1.17.1 `portfolio_architect.zip` was byte-identical to the manual Home Assistant
drop-in and therefore contained an additional
`custom_components/portfolio_architect/` wrapper. HACS had already selected the
integration directory as its extraction target, so that wrapper produced a
nested, ignored copy instead of replacing the active integration files.

The integration runtime, portfolio calculations, cost-aware execution, entities,
dashboard behavior, source schemas, Gateway protocols, and v1.17.1 security
hardening are otherwise unchanged.

## Correct channel-specific archive layouts

- `portfolio_architect.zip`, the HACS release asset, now contains the integration
  files directly at the ZIP root: `manifest.json`, `__init__.py`, `const.py`,
  `engine/`, `translations/`, `brand/`, and the remaining integration files.
- `portfolio-architect-v1.17.2-ha-dropin.zip`, the manual installation archive,
  deliberately retains the `custom_components/portfolio_architect/` wrapper so
  it can be extracted over the Home Assistant `/config` directory.
- The two archives contain the same integration payload after normalizing that
  channel-specific prefix, but they are intentionally no longer byte-identical.

## Regression prevention

- The release builder now stages the HACS and manual drop-in archives
  independently.
- Release verification rejects a HACS asset containing a `custom_components/`
  prefix or missing a root-level integration manifest.
- Verification rejects a manual drop-in without the expected wrapper.
- Verification compares every integration file and SHA-256 between both archives
  after prefix normalization.
- An executable regression test deliberately substitutes the manual drop-in for
  the HACS asset and requires verification to fail.

## Recovery after an attempted v1.17.1 HACS download

Before downloading v1.17.2, remove only the incorrectly nested directory:

```bash
rm -rf /config/custom_components/portfolio_architect/custom_components
```

Do not remove the outer `/config/custom_components/portfolio_architect`
directory. Download v1.17.2 in HACS, verify that the active root-level version
markers report `1.17.2`, confirm that only one Portfolio Architect
`manifest.json` exists, and then restart Home Assistant.

## Compatibility

- No configuration migration.
- No payload, REST portfolio, Gateway health, allocation-overview, or cost-model
  schema change.
- No entity-ID or unique-ID change.
- No dashboard replacement required.
- Gateway App 1.16.1 and later remain protocol-compatible.
