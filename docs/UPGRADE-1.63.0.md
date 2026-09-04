# Upgrade to Portfolio Architect v1.63.0

v1.63.0 is a static reference-dashboard architecture/presentation release. It does not change configuration schemas, provider acquisition, planner behavior, freshness policy, Gateway wire contracts, or private-PKI trust.

## Integration and Gateway Apps

1. Update Portfolio Architect through HACS to v1.63.0 and restart Home Assistant normally.
2. Align the installed Comdirect, DKB, Trade Republic, and Generic Import Gateway Apps to v1.63.0 for package-version consistency. No provider reauthentication, statement/CSV re-import, acquisition-mode change, or private-state reset is required solely because of this release.
3. Confirm the same configured providers remain healthy and authoritative with the same acquisition modes, evidence timestamps/freshness policy, and planner economics as before.

## Dashboard adoption is deliberate

HACS does not overwrite user-owned Lovelace YAML. The integration upgrade therefore does **not** automatically replace an imported Portfolio Architect dashboard.

To adopt the v1.63.0 reference presentation, bulk-replace the copied dashboard YAML with exactly one of:

- `portfolio-architect-v1.63.0-dashboard-en.yaml` for English only;
- `portfolio-architect-v1.63.0-dashboard-de.yaml` for German only;
- `portfolio-architect-v1.63.0-bilingual-dashboard.yaml` for the established combined EN/DE views.

For a single-language installation, the matching single-language artifact is preferred because Home Assistant then loads only one full view. The combined artifact remains supported and preserves the EN/DE view paths.

The v1.63.0 dashboard changes are presentation-only: zero accepted exceptions now show a green no-review-required state, and exception review date tiles remain hidden until an accepted exception actually exists.

## No source-tree generator on Home Assistant

Do not copy `dashboard/src/`, `dashboard/manifest.json`, or the build tools into Home Assistant as a dashboard dependency. They are repository/release authoring inputs only. Install the generated static YAML artifact.

## Rollback

The integration can be rolled back using the normal HACS release mechanism subject to the existing supported-version rules. Dashboard YAML is user-owned, so retain a copy of your previous Lovelace configuration if you want to restore its exact presentation independently of the integration version.
