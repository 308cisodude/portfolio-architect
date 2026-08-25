# v1.52.0 validation

Portfolio Architect v1.52.0 is prepared from the exact published/live-accepted
v1.51.1 tracked-source baseline. The release changes Gateway maturity metadata and
capability-scoped presentation only: DKB and Trade Republic become stable Apps,
Generic Import remains experimental, and the DKB anonymous FinTS probe is explicitly
marked experimental/research inside the otherwise-stable DKB App.

Release validation requires:

- all integration/common Gateway/all four App current-version markers align to
  1.52.0 while historical release documentation remains historical;
- Comdirect, DKB and Trade Republic App `stage` values are `stable`;
- Generic Import App `stage` remains `experimental`;
- DKB Ingress explicitly marks the anonymous BPD probe `EXPERIMENTAL · RESEARCH ONLY`;
- authenticated DKB FinTS acquisition remains disabled and cannot replace or fall
  back from CSV evidence;
- the bundled wholly synthetic generic CSV example parses successfully under the
  Generic Import default mapping without creating provider cash or credentials;
- current provider documentation reflects the four-App architecture and
  capability-scoped maturity labels;
- the SPDX SBOM describes all four Gateway Apps;
- provider acquisition, v1.48 freshness, independent evidence clocks, planner
  economics, wire schemas, private-PKI/DNS pinning, source-set atomicity/LKG and the
  advisory-only boundary remain unchanged;
- complete regression tests, Python compilation, structured-file parsing and
  `git diff --check` pass;
- source/release privacy, publication readiness, provider-App source parity,
  deterministic release builds, and exact Git overlay/binary-patch replay all pass.

Protected GitHub workflows remain authoritative for complete-history/Gitleaks and
actual provider-App Docker/private-PKI smoke execution when unavailable locally.
