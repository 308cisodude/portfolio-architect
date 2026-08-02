# Upgrade to Portfolio Architect 1.12.2

This publication-facing fix release improves multi-source labels, DKB export
selection, and dashboard consistency. Calculations, entity IDs, payload schema 8,
REST schema 1, and the Home Assistant last-known-good cache are unchanged.

## Changes

- Comdirect REST provenance is displayed as **Comdirect**, never as an endpoint.
- One DKB source is displayed as **DKB**; multiple distinct DKB depots are numbered.
- When several exports of the same DKB depot are configured, only the newest
  source-owned export date is counted. Same-date conflicting files fail closed.
- Depot numbers are used only as transient in-memory comparison keys and are
  never persisted, logged, diagnosed, or exposed as entity attributes.
- Outside-plan holding tiles use a consistent two-column layout with concise labels.

Update the integration drop-in and replace the dashboard YAML. The Gateway App
contains no runtime changes and may remain on 1.12.1.
