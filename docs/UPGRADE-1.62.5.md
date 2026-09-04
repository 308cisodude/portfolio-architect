# Upgrade to Portfolio Architect v1.62.5

v1.62.5 is a narrow Home Assistant integration hotfix for coordinator configuration metadata. It does not change provider acquisition, wire schemas, portfolio policy semantics, broker routing, freshness thresholds or Gateway trust.

## What changes

Portfolio Architect continues to require exactly these four configuration documents:

- `portfolio.yaml`
- `policy.yaml`
- `instruments.yaml`
- `broker.yaml`

`exceptions.yaml` remains optional. In v1.62.4, the coordinator metadata/LKG fingerprint path accidentally treated its absence as if a required configuration file were missing. v1.62.5 includes optional files in metadata only while they exist. A missing required file still fails closed.

## LG clean-room acceptance fixture

The current LG installation is an ideal live fixture: it has a valid four-file first-run configuration, no `exceptions.yaml`, one attached Generic source and normal v1.62.4 entities that remained unavailable because coordinator metadata rejected the optional-file absence.

After updating Portfolio Architect and Generic Import to v1.62.5 and restarting Home Assistant once:

1. Do not create `exceptions.yaml`.
2. Confirm the same four files remain present and unchanged.
3. Confirm the existing Generic source remains attached with the same immutable provider ID.
4. Confirm normal coordinator entities populate and `source_healthy` no longer fails solely because `exceptions.yaml` is absent.
5. Confirm logs contain no new `Portfolio configuration files are unavailable` message for the valid four-file directory.
6. Add a temporary synthetic `exceptions.yaml` only if deliberately testing fingerprint participation; it is not required for normal operation.

Then continue the remaining Generic graduation tests: independent cash evidence, rename/immutable identity, restart persistence, rejected-import atomicity and second-profile discovered-supplemental behavior.

## HH production

An established HH configuration with a real `exceptions.yaml` (if present) remains valid and its fingerprint continues to include that file. If HH has no `exceptions.yaml`, v1.62.5 simply stops treating that valid absence as an error.

Update the Portfolio Architect integration directly to v1.62.5, restart Home Assistant once, verify the existing YAML/source/broker topology is unchanged, then align the provider Apps to v1.62.5. Re-import the current Trade Republic cash statement after the TR App is aligned; the v1.62.3 German month parser remains unchanged and should accept the live-observed `Sept.` statement.

No dashboard YAML replacement and no freshness-threshold change are required.
