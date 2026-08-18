# Portfolio Architect 1.32.0

Version 1.32.0 is the **provider freshness and diagnostics foundation** prepared from the
exact immutable v1.31.2 source baseline. It improves the explanation and provider-specific
handling of stale or rejected evidence without relaxing Portfolio Architect's existing
fail-closed investment-actionability rules.

## Per-source freshness evidence

Portfolio Architect already makes a multi-source plan non-actionable when the oldest
contributing source lies outside the configured freshness window. Version 1.32.0 keeps that
rule unchanged and exposes bounded evidence explaining it.

The Portfolio sources and Snapshot freshness entities now include per-source evidence with:

- source ID, provider and bounded label;
- provider evidence kind (`live_api`, `imported_statement`, `imported_csv`, bounded Gateway
  snapshot or other);
- source `generated_at` timestamp and locally derived age;
- the currently applicable aggregate age threshold; and
- whether that source is inside the age threshold.

When age-threshold freshness is the active gate, additive attributes identify only the
sources currently blocking actionability and provide bounded English/German summaries.
For the live acceptance topology that motivated this release, the DKB CSV source is the only
stale source while the newer Comdirect and Trade Republic evidence remains inside the same
168-hour window.

This is **observability, not a policy change**. The engine still evaluates freshness from the
oldest contributing source, and one stale source can still make the complete investment plan
non-actionable. Version 1.32.0 does not introduce per-provider freshness limits and does not
ignore a stale source because its monetary contribution is small.

## Native dashboard blocker explanation

The English/German reference dashboard now uses built-in Tile `state_content` attributes to
show the actual stale-source/actionability detail instead of only a generic unavailable or
outside-freshness state. No custom card, frontend template, JavaScript or CSS dependency is
introduced.

The dashboard YAML therefore changes in this release. Existing dashboards remain runtime
compatible, but replacing the supplied reference dashboard is required to display the new
freshness/actionability explanation.

## Provider diagnostic policy

`docs/PROVIDER-DIAGNOSTICS.md` defines a shared security boundary for provider-specific
operator diagnostics:

- retain only explicitly classified and bounded evidence;
- keep persistent diagnostic state App-private and mode `0600`;
- never persist raw upstream response bodies merely for troubleshooting;
- never expose credentials, tokens, cookies, PIN/TAN material, account/depot identifiers or
  private holdings/monetary values through diagnostics;
- keep provider App Ingress actions/navigation inside the App namespace; and
- replace obsolete failure evidence after a successful operation rather than growing an
  accidental diagnostic archive.

The policy deliberately permits provider-specific retention decisions rather than forcing one
mechanism onto every provider.

### Trade Republic

The Trade Republic App now persists only its **latest bounded statement-import outcome** next
to the existing private provider snapshot. Accepted, rejected and internal-error outcomes use
a strict allowlist/genericization contract. Unexpected parser text cannot be persisted or
echoed back after reopening the App, even if a diagnostic state file is malformed or tampered
with. A later successful import replaces the previous failure evidence.

The uploaded `DEPOTAUSZUG` PDF is still parsed in memory and is not stored. Version 1.32.0
also deliberately does **not** persist a PDF SHA-256: a private financial document's stable
fingerprint is unnecessary diagnostic identity and would weaken data minimization. This
release does not move PDF parsing into Portfolio Architect.

### Comdirect

The established Comdirect runtime is audited and regression-protected against the same
policy. Its authenticated upstream path continues to expose only bounded failure classes and
approved OAuth/session rejection reasons; remote response bodies, credentials, qSession
state and private account material are not retained for diagnostics. Ingress navigation
continues to use the App-relative root. No new authenticated-response fingerprint or free-text
persistence is added.

### DKB

The live-accepted v1.31.2 registered anonymous FinTS diagnostic contract is unchanged apart
from normal package/version metadata. Its anonymous bounded `HIRMG`/`HIRMS` return evidence
and decoded-response fingerprint remain appropriate to that deliberately non-authenticated
probe. DKB remains experimental, manual-only and non-live. The current `9078` product-not-
registered result is capability-inconclusive while the issued product identity propagates.

A positive future `HIWPDS` BPD result would still be only bank-level evidence. Authenticated
user capability/UPD validation and DKB-App decoupled authentication remain later gates. DKB
live Gateway acquisition remains a later authenticated milestone; v1.32.0 adds no holdings
request.

## Preserved contracts

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- the oldest-contributing-source freshness/actionability rule: unchanged
- configured freshness threshold semantics: unchanged
- v1.31 canonical accumulating Robotics target: unchanged
- v1.31.1 ISIN-only outside-scope holding validation: unchanged
- v1.31.2 DKB registered FinTS probe semantics: unchanged
- DKB live Gateway acquisition remains a later authenticated milestone
- Comdirect acquisition, OAuth/session maintenance, PhotoTAN and authorized cash: unchanged
- Trade Republic accepted provider snapshot and REST serving semantics: unchanged
- verified private-PKI HTTPS, bearer authentication, Supervisor trust discovery, DNS pinning
  and no-plaintext fallback: unchanged
- LKG behavior and investment actionability fail-closed behavior: unchanged

No trading, order, transfer, payment, or transaction-history capability is added. No automatic
sell capability is added. The historical `v1.19.0-rc2` experimental brokerage diagnostic
branch remains excluded and is not promoted by this release.

## Upgrade

The integration and all three official Gateway Apps are version-aligned to 1.32.0. No
portfolio/configuration migration, Comdirect reauthentication, Trade Republic statement
re-import or DKB registration re-entry/probe is required merely because of this upgrade.
Replace the supplied bilingual dashboard YAML if you want the new visible blocker detail.

See `docs/UPGRADE-1.32.0.md`.
