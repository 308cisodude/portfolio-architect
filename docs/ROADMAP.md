# Portfolio Architect roadmap

This roadmap records intended sequencing rather than a compatibility promise. Each milestone remains subject to design, security review, tests, and live acceptance.

## v1.22.0 — publication and privacy hardening

Completed: source/history/artifact privacy gates and immutable secret scanning are release invariants.

## v1.23.0 — provider-aware Gateway foundation

Completed: the hardened Gateway server consumes a provider-neutral runtime contract and health schema 6 carries bounded provider identity. The existing Comdirect App retained its historical slug/private state.

## v1.24.0 — distinct provider Gateway Apps

Completed with live-acceptance follow-up in v1.24.1.

- Publish three separate Supervisor App identities in this order: **Portfolio Architect Gateway — Comdirect**, **Portfolio Architect Gateway — DKB**, and **Portfolio Architect Gateway — Trade Republic**.
- Keep Comdirect stable and updateable in place under `portfolio_architect_gateway`.
- Give DKB and Trade Republic independent slugs and `/data/gateway` private volumes.
- Reuse byte-identical audited provider-neutral server/model/storage/runtime modules in each provider build context while keeping provider-specific code out of the DKB/TR shells.
- Ship DKB/TR as experimental, manual-only, fail-closed provider shells. They establish installable identities and future in-place upgrade paths but deliberately do not claim live acquisition yet.
- Publish separate release ZIPs for all three provider Apps.
- Preserve payload schema 8, REST portfolio schema 1, Gateway health schema 6, existing Home Assistant entity IDs, Comdirect cash/LKG behavior, and the v1.22 privacy gate.

## v1.24.1 — provider-shell startup hotfix

Completed: remove the accidental runtime import of the Comdirect-only configuration module from the reduced DKB/TR package, and require isolated-package import plus running-container smoke tests in protected CI.

## v1.25.0 — Trade Republic statement import

Add local import support for supported Trade Republic statement documents inside the separate Trade Republic Gateway App and map validated holdings into the provider-neutral snapshot model.

Privacy is a hard design constraint:

- real Trade Republic statements remain private input and are never committed;
- public tests use wholly synthetic documents/fixtures only;
- account-holder data, addresses, account/depot identifiers, tax identifiers and other attribution fields are excluded from public payloads, diagnostics, logs and release artifacts;
- unknown or ambiguous document structures fail closed rather than guessing financial data.

The exact supported statement families and import semantics will be fixed during the v1.25.0 design phase.

## Later provider acquisition work

The DKB App requires its own supported acquisition/import design before it becomes a live source. Portfolio Architect currently supports one primary REST source plus its established supplemental-source model; simultaneous primary REST Gateways remain a separate Home Assistant aggregation/configuration milestone.
