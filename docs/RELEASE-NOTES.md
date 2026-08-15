# Portfolio Architect 1.27.2

Version 1.27.2 fixes the Home Assistant config-flow eligibility defect found during
live acceptance of the v1.27.1 verified-HTTPS release. The v1.27 Gateway Apps
successfully generated private-PKI material, served HTTPS and published Supervisor
discovery, but an existing Portfolio Architect entry remained on legacy HTTP because
Home Assistant's manifest-level `single_config_entry` guard prevented the `hassio`
discovery flow from being initialized at all.

The hotfix removes that coarse framework guard and preserves the intended single-entry
architecture explicitly in Portfolio Architect's manual setup path. Supervisor
discovery can therefore reach `async_step_hassio` for the one existing entry and run
the already-established verified-HTTPS migration logic.

## Precise config-flow boundary

Portfolio Architect still supports exactly one normal config entry. `async_step_user`
now checks for any existing Portfolio Architect entry and aborts manual setup with the
existing `already_configured` result before creating another entry. The stable
`portfolio_architect` unique ID and duplicate-unique-ID guard remain in place as a
second protection.

The manifest no longer declares `single_config_entry` because Home Assistant applies
that option before dispatching *any* new config flow, including trusted Supervisor
`hassio` discovery. Removing the manifest shortcut therefore does not authorize a
second Portfolio Architect instance; it makes the discovery flow reachable while the
integration itself enforces manual single-instance cardinality.

## Verified HTTPS migration remains fail closed

The existing v1.27 migration sequence is unchanged after the flow is allowed to run:

- Supervisor discovery must parse as transport-discovery schema 1;
- provider identity, hostname, port, fixed path, public CA and CA fingerprint must
  validate;
- the discovery must match the configured legacy source network identity;
- the discovered HTTPS health endpoint must validate with hostname checking, the
  discovered private CA and the already-stored bearer token before configuration is
  written;
- a different CA for an already secured source is refused; and
- a migrated source never automatically falls back to plaintext HTTP.

Supplemental discovery also fails closed when the same provider is already represented
under another network identity. A DKB App discovery is not offered as a new source when
the portfolio already contains configured DKB CSV input.

## Production scope

Gateway TLS/runtime behavior is unchanged from v1.27.1 apart from normal 1.27.2
version metadata. There is no new CA, certificate, bearer-token, OAuth/session,
PhotoTAN, provider-acquisition, statement-import, portfolio-calculation, entity,
dashboard or wire-schema behavior.

Compatibility and security invariants remain:

- payload schema 8: unchanged;
- REST portfolio schema 1: unchanged;
- Gateway health schema 6: unchanged; health schemas 1–5 remain supported where previously supported;
- one Portfolio Architect config entry: retained, now enforced in the user flow;
- bearer authentication remains independent of TLS;
- private CA keys remain App-private;
- source atomicity and Home Assistant LKG behavior: unchanged;
- Comdirect acquisition and authorized-cash semantics: unchanged;
- Trade Republic `DEPOTAUSZUG` statement import: unchanged; this release does not move PDF parsing into Portfolio Architect;
- DKB Gateway remains experimental/manual-only/fail-closed with no live acquisition; DKB live Gateway acquisition remains a later provider-specific milestone;
- No trading, order, transfer, payment, or transaction-history capability is added.
- The historical experimental `v1.19.0-rc2` brokerage diagnostics/fee-probe work remains separate and is not promoted by this release.

The upgrade and live-recovery path is documented in `docs/UPGRADE-1.27.2.md`. No
reference-dashboard YAML migration is required.
