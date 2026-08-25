# Upgrade to Portfolio Architect 1.53.0

Version 1.53.0 adds a provider-neutral acquisition-method control plane to the
fully live-accepted v1.52.0 Gateway architecture. Provider identity remains stable:
Portfolio Architect still sees one `comdirect`, one `trade_republic`, one `dkb`,
and any separately configured Generic Import provider. Acquisition method selection
is owned by each provider Gateway, not by the Home Assistant integration.

## What changes

Gateway health schema 8 adds bounded read-only metadata for:

- the active acquisition method;
- the provider-defined method inventory;
- readiness and explicit activation eligibility;
- `fallback_policy: none`; and
- the previous method plus UTC timestamp/reason of the last successful explicit
  operator switch when such history exists.

Portfolio Architect displays this state in diagnostics/source attributes but has no
API or action for changing it.

Comdirect is the first switchable provider. `live_api` and `csv` remain mutually
exclusive. While live API is authoritative, both static holdings and cash CSV
snapshots can be staged privately without affecting the canonical PA snapshot. CSV
becomes READY only when both evidence families exist. An explicit activation is
atomic with canonical publication; failure restores the exact prior control state. A
private pending marker also makes interruption fail closed across an App stop/restart:
the prior method is restored and an ambiguous cached canonical snapshot is discarded
before normal startup refresh. Corrupt inactive CSV state is treated as not-ready and
cannot disrupt active live acquisition. There is no automatic fallback between API
and CSV.

DKB remains `csv` active while `fints` is research-only and non-activatable. Trade
Republic remains `pdf` active while `live_api` is unavailable. Generic Import has a
single fixed `csv` method. Authenticated DKB FinTS is not enabled by this release.

## Normal upgrade

1. Update **Portfolio Architect** through HACS to **1.53.0** and restart Home
   Assistant once.
2. Update the installed Comdirect, DKB and Trade Republic Gateway Apps to **1.53.0**
   in place, preserving App-private state, trust material and imported evidence.
3. If Generic Import is installed for a real use case, align it to 1.53.0 in place;
   do not install it solely for this release.
4. Do not reauthenticate Comdirect or re-import provider evidence solely because of
   the software upgrade when the current source is healthy.
5. No dashboard YAML replacement is required.

## Planned live acceptance

First prove the upgrade is non-disruptive: the real source set must still contain
exactly `comdirect`, `trade_republic` and `dkb`, with acquisition modes
`live_api`, `pdf` and `csv`, normal freshness thresholds, healthy sources and
unchanged planner/cash-routing semantics.

Then exercise the new control plane using Comdirect:

1. Keep `live_api` active.
2. Import a current Comdirect holdings CSV and current Comdirect cash CSV into the
   inactive static section.
3. Confirm CSV becomes READY but Portfolio Architect continues to report
   `comdirect` exactly once with `acquisition_mode: live_api`.
4. Explicitly activate CSV in the Comdirect Gateway. Confirm one `comdirect`
   provider remains configured, the canonical source changes to `csv`, and the
   staged static evidence is the published snapshot.
5. Explicitly activate live API again. The Gateway must perform a real live read,
   return to `live_api`, and retain `fallback_policy: none`.
6. Confirm DKB reports `csv` active plus non-activatable research-only `fints`, and
   Trade Republic reports `pdf` active plus unavailable non-activatable `live_api`.
7. Do not deliberately damage production credentials or App-private state merely to
   exercise rollback; publication-failure, corrupt-inactive-candidate and interrupted-
   activation recovery paths are covered by executable regression tests.

A pre-v1.53 Comdirect installation already running in legacy holdings-only CSV mode
remains readable after upgrade. Once another acquisition method is explicitly
activated, returning to CSV requires a complete staged holdings-and-cash candidate.

## Generic Import isolation

Generic Import remains experimental. If it is installed only for a standalone smoke or there is no real mapped-CSV use case, do **not** add its discovery card/source to the production Portfolio Architect config entry; leave the existing provider set unchanged and uninstall the temporary App after the isolated exercise.
The isolated Generic Import exercise must not alter the real production portfolio or its configured provider set.
If Generic Import is used only for the documented synthetic check, it should be uninstalled after this standalone smoke test.
