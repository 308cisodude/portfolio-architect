# Portfolio Architect dashboard

Portfolio Architect v1.63.0 authors dashboard behavior once and generates ordinary static Home Assistant Lovelace YAML per locale. Home Assistant receives only the generated YAML; no dashboard generator, include processor, custom parser, JavaScript, locale helper, or build-time dependency runs on the Home Assistant host.

## Installable dashboards

The repository keeps three generated reference artifacts:

- `generated/portfolio-architect-dashboard-en.yaml` — English only;
- `generated/portfolio-architect-dashboard-de.yaml` — German only;
- `generated/portfolio-architect-dashboard-en-de.yaml` — combined EN/DE views.

`bilingual-dashboard.yaml` is retained as a byte-identical compatibility alias for the combined generated dashboard.

For a single-language installation, prefer the matching EN-only or DE-only artifact. That keeps the Lovelace configuration loaded by Home Assistant to roughly one-language size. Adding another locale later therefore adds a small source catalog plus another generated single-language artifact; it does not multiply shared card logic or enlarge an existing English/German dashboard.

## Source architecture

Authoritative source lives under `dashboard/src/`:

```text
src/
  shared/
    view.yaml
    sections/
      01-investment-plan.yaml
      02-portfolio-policy-compliance.yaml
      03-target-architecture.yaml
      04-runtime-health.yaml
      05-total-portfolio-value.yaml
      06-outside-current-plan-scope.yaml
      07-current-plan-allocation.yaml
      08-plan-target-allocation.yaml
      09-current-portfolio-allocation.yaml
  i18n/
    en.yaml
    de.yaml
  overlays/
    en.yaml
    de.yaml
```

The shared source contains the complete card, entity, condition, color, icon, bar and layout behavior exactly once. User-facing strings are represented by bounded `$i18n` markers and resolved from locale catalogs. The current EN/DE reference has 100 matched translation keys.

Locale-specific technical differences that are not translations belong in a bounded overlay. English is the structural base and needs no overlay operations; German currently needs 40 JSON-Pointer operations for technical presentation attributes such as German-specific `state_content` fields. These details stay out of translator-facing catalogs.

Build a dashboard with:

```sh
python tools/build_dashboard.py --locale en --output dashboard/generated/portfolio-architect-dashboard-en.yaml
python tools/build_dashboard.py --locale de --output dashboard/generated/portfolio-architect-dashboard-de.yaml
python tools/build_dashboard.py --locale all --output dashboard/generated/portfolio-architect-dashboard-en-de.yaml
```

Release packaging reruns the generator and fails closed if committed generated outputs are stale. Regression tests also lock catalog parity, marker coverage, bounded overlays, deterministic generation, and canonical semantic hashes.

To start a new locale without copying card logic:

```sh
python tools/scaffold_dashboard_locale.py es
```

The scaffold intentionally writes `__TODO__` catalog values and an empty overlay. The build refuses incomplete catalogs. A locale is added to `dashboard/manifest.json` only after translation and acceptance are complete.

## Native-card contract

The reference dashboard uses only native Home Assistant Heading, Tile, Conditional, Glance, Entities, Entity-filter, and Markdown cards. Markdown is used only as a bounded renderer for the integration-owned execution-path text; routing and funding decisions remain outside Lovelace. There are no custom cards, `card-mod`, custom JavaScript, or nested fixed-column Grid cards.

Sections rearrange across desktop, tablet, and smartphone widths. Dynamic target, outside-scope, and policy inventories use bounded presentation-slot entities plus native `entity-filter` cards. Stable target/holding identity remains on target-ID/position-ID entities and in slot attributes.

## Policy-exception presentation

At zero accepted exceptions, the v1.63.0 reference dashboard renders the exception count in green and explicitly shows **Exception review not required** / **Ausnahmeprüfung nicht erforderlich**. The due and overdue exception-review tiles are gated on `accepted_exception_count > 0`, so a review date is not presented when no accepted exception exists.

When accepted exceptions exist, their bounded detail presentation remains clickable through native Home Assistant more-info. Long documented rationales stay on the original policy-finding entity and in diagnostics rather than being duplicated into the primary dashboard.

## Reference-dashboard ownership

Generated YAML is static reference configuration, not integration-owned Home Assistant state. Once copied/imported into a Home Assistant dashboard, that copy is user-owned. HACS updates only the integration package; Portfolio Architect never silently overwrites a user's Lovelace configuration.

When a release changes the reference layout, its upgrade guide identifies the change. Users can deliberately bulk-replace the copied dashboard YAML or retain their customized version.
