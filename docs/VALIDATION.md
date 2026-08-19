# v1.35.1 validation

Portfolio Architect v1.35.1 is a narrow resilience hotfix prepared from the exact published
v1.35.0 tracked-source baseline.

## Required automated evidence

- integration, engine, common Gateway and all three official App package versions align at
  `1.35.1`;
- a real `ConnectionResetError` injected at the Comdirect HTTPS opener boundary becomes the
  established bounded retryable `RemoteApiError` with `status == 0` and `operation ==
  "oauth_refresh"`;
- an unexpected ordinary exception injected into one session-maintenance iteration cannot
  terminate the worker; a later iteration still runs successfully;
- the containment diagnostic does not include arbitrary exception text;
- existing v1.27.4 five-minute maintenance cadence, conclusive refresh-rejection latch and
  provider-specific wiring regressions remain green;
- the two remaining German allocation-chart labels use `Robotik · Thes.` and no English
  accumulating-Robotics label remains in the German standalone dashboard;
- all v1.35.0 provider-scoped funding, DKB probe-fingerprint and dashboard regressions remain green;
- complete Python regression suite, Python compilation, JSON/YAML parsing, `git diff --check`,
  strict publication readiness, source privacy, release verification and release-artifact privacy
  pass;
- three independent release builds are byte-identical; and
- the Git overlay and binary patch independently reproduce the exact final tracked tree from the
  v1.35.0 baseline, including executable-bit semantics.

## Live acceptance

1. Start from a healthy live v1.35.0 installation with all three provider Apps aligned.
2. Update Portfolio Architect to v1.35.1 and restart Home Assistant once.
3. Keep the real `broker.yaml` on its existing schema unless a separate funding-topology change is
   deliberately planned; no schema-3 migration is part of this hotfix.
4. Update Comdirect to v1.35.1 in place and confirm the existing private CA, bearer token,
   OAuth/session state, selected account and authorized-cash policy survive.
5. Confirm Comdirect remains `OK / Live` across repeated scheduled portfolio refreshes and
   maintenance cycles without upgrade-induced PhotoTAN reauthentication.
6. Align Trade Republic and DKB to v1.35.1 in place; do not re-import or re-probe solely for this
   release.
7. A deliberate connection-reset fault injection is not required in production. If a natural
   transient reset later occurs, confirm the maintenance worker remains active afterward.

Local Docker availability is environment-dependent; protected GitHub workflows remain authoritative
for actual provider-App Docker/private-PKI smoke execution when local Docker is unavailable.
