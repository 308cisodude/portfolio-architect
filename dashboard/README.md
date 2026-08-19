# Portfolio Architect dashboard

`bilingual-dashboard.yaml` contains matched English and German Sections views
labelled `EN` and `DE`.

The reference dashboard uses only native Home Assistant Heading, Tile,
Conditional, Glance, and Distribution cards. It avoids Markdown, custom cards,
Entities cards, Entity-filter cards, JavaScript, and nested fixed-column Grid
cards. Sections rearrange across desktop, tablet, and smartphone widths.

## Reference-dashboard ownership

This YAML is a static reference configuration, not integration-owned Home Assistant
state. Once it is copied/imported into a Home Assistant dashboard, that copy is
user-owned configuration. HACS updates only the custom integration package; neither
HACS nor Portfolio Architect automatically overwrites an imported dashboard.

When a future release changes the reference layout, the corresponding upgrade guide
will say so explicitly. Users can then review/import the newer YAML deliberately,
without risking silent replacement of local dashboard customizations.

The investment-plan section shows budget, frequency, contribution per execution,
execution count, scheduled execution, current actionability, last evaluation, and current buy recommendations. Runtime
health shows the active source provider, last evaluation, snapshot freshness-window status, next plan review, Gateway operating mode, snapshot age, next live
refresh, refresh duration and trigger, and conditional last-known-good,
refresh-running, operator-attention, recovery-action, last-failure, and
refresh-overdue indicators. Schedule cards remain hidden until a recurring
execution schedule is configured in Portfolio Architect options.

The policy-compliance section prioritizes actionable operator context rather than
raw evaluation counters. The aggregate Checks entity remains native Home Assistant
state but is omitted from the primary reference layout. The existing optimisation-
opportunity count appears only as a compact heading badge, not as a competing tile.
The dashboard pairs the accepted-exception count with its concrete exception, then the
last decision with the next (or overdue) **exception** review. A native conditional subtitle separates
that governed exception lifecycle from non-critical optimisation opportunities and shows
the existing opportunity count as a compact heading badge. The subtitle is hidden when
there are no opportunities. Concrete opportunity tiles remain full-width below it.

For German dashboards, actionable values that intentionally become unavailable
during source degradation are rendered through bounded presentation attributes on
the always-available actionability entity. Their more-info actions still target the
original monetary/count entities, whose fail-closed availability semantics remain
unchanged.

v1.36 consumes the first-class `sensor.portfolio_architect_presentation_model` through bounded diagnostic presentation-slot entities. The reference dashboard enumerates only generic bounded slot candidates and lets native Home Assistant `entity-filter` cards select the currently available target, outside-scope and active-policy inventory. Stable target/holding identity remains on the target-ID/position-ID entities and is repeated in slot attributes. No `auto-entities`, card-mod, custom JavaScript or custom-card dependency is required. User-owned dashboard copies remain opt-in and are never overwritten by HACS.

## Allocation overview contract

`sensor.portfolio_architect_allocation_overview` is intentionally not rendered as
a separate reference-dashboard card. The existing native allocation, drift, and
investment-plan sections already present the actionable information without a
parallel summary. The aggregate sensor remains available for templates,
automations, diagnostics, and future native dashboard work.

## Policy-exception presentation

The accepted Robotics exception is shown as a compact native tile backed by a
bounded detail entity. Tapping the tile opens a normal Home Assistant more-info
dialog with the instrument, policy rule, observed and expected values, decision
date, and review date. The long documented rationale remains only on the original
policy-finding entity and in diagnostics, so the dashboard stays responsive and
avoids the former horizontally scrolling dialog.
