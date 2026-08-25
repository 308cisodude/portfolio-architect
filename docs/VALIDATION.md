# v1.53.0 validation

Portfolio Architect v1.53.0 is prepared from the exact published/live-accepted
v1.52.0 tracked-source baseline. The release adds a provider-neutral acquisition
control plane while preserving one canonical Portfolio Architect provider per bank.
Comdirect is the first provider with explicit operator-controlled switching between
`live_api` and a complete staged `csv` candidate. Portfolio Architect consumes the
control state read-only and does not gain acquisition-management authority.

Release validation requires:

- all integration/common Gateway/all four App current-version markers align to
  1.53.0 while historical release documentation remains historical;
- Gateway health schema 8 adds only bounded acquisition-control metadata while
  schemas 1 through 7 remain accepted;
- every schema-8 control document has exactly one active ready method, unique
  bounded method IDs, explicit `fallback_policy: none`, and complete-or-absent
  bounded operator switch history;
- Comdirect inactive CSV becomes activatable only when both holdings and cash
  evidence are staged, while a legacy already-active holdings-only CSV state remains
  readable for upgrade compatibility;
- Comdirect activation validates the candidate, persists the method change and
  publishes the canonical snapshot under one acquisition lock; publication failure
  restores the exact prior acquisition-control state;
- a private pending-activation marker makes interrupted Comdirect switches crash-safe:
  startup restores the recorded prior mode, discards any ambiguous cached canonical
  snapshot before `GatewayState` loads it, and then uses the normal fresh startup refresh;
- corrupt inactive Comdirect CSV candidate state is reduced to `not_ready` and cannot
  disrupt the active live source; expected activation failures are bounded Ingress
  outcomes and leave the previous method authoritative;
- switching methods never changes provider identity and never creates an automatic
  fallback path;
- DKB advertises `csv` active/ready and `fints` research-only/non-activatable;
- Trade Republic advertises `pdf` active/ready and `live_api` unavailable/non-activatable;
- Generic Import advertises its single fixed `csv` method;
- authenticated DKB FinTS acquisition remains disabled and the anonymous BPD probe
  remains a separate experimental/research-only gate;
- Portfolio Architect exposes acquisition control state diagnostically but adds no
  provider-management POST/action or money-moving capability;
- current provider documentation and the SPDX SBOM describe the v1.53.0 contract;
- v1.48 freshness, independent evidence clocks, planner economics, REST/payload/
  presentation/broker schemas, private-PKI/DNS pinning, configured-source atomicity,
  Home Assistant LKG and the advisory-only boundary remain unchanged;
- complete regression tests, Python compilation, structured-file parsing and
  `git diff --check` pass;
- source/release privacy, publication readiness, provider-App source parity,
  deterministic release builds, and exact Git overlay/binary-patch replay all pass.

Protected GitHub workflows remain authoritative for complete-history/Gitleaks and
actual provider-App Docker/private-PKI smoke execution when unavailable locally.
