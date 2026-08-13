# Portfolio Architect dashboard

`bilingual-dashboard.yaml` contains matched English and German Sections views
labelled `EN` and `DE`.

The reference dashboard uses only native Home Assistant Heading, Tile,
Conditional, Glance, and Distribution cards. It avoids Markdown, custom cards,
Entities cards, Entity-filter cards, JavaScript, and nested fixed-column Grid
cards. Sections rearrange across desktop, tablet, and smartphone widths.

The investment-plan section shows budget, frequency, contribution per execution,
execution count, scheduled execution, current actionability, last evaluation, and current buy recommendations. Runtime
health shows the active source provider, last evaluation, snapshot freshness-window status, next plan review, Gateway operating mode, snapshot age, next live
refresh, refresh duration and trigger, and conditional last-known-good,
refresh-running, operator-attention, recovery-action, last-failure, and
refresh-overdue indicators. Schedule cards remain hidden until a recurring
execution schedule is configured in Portfolio Architect options.

The complete-portfolio Distribution card and per-instrument plan cards explicitly
reference the current sample configuration. New holdings and plan instruments
receive entities automatically but must be added to the static native dashboard
YAML to appear in those lists.

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
