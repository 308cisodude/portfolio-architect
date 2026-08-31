# Upgrade to Portfolio Architect v1.61.1

v1.61.1 is a narrow Home Assistant-side Supervisor-discovery lifecycle hotfix prepared from the exact published v1.61.0 baseline. It fixes the misleading supplemental discovery card exposed during v1.61.0 live acceptance **and** removes the inherited Comdirect-only first-run bootstrap assumption.

## Provider-neutral first installation

Portfolio Architect still has exactly one canonical Home Assistant config entry, but **Comdirect is not required**. When no Portfolio Architect entry exists, any validated Portfolio Architect Gateway discovered through Supervisor may bootstrap that singleton entry.

Examples:

- DKB-only installation: DKB can create the first Portfolio Architect entry.
- Trade-Republic-only installation: Trade Republic can create the first Portfolio Architect entry.
- Comdirect-only installation: Comdirect continues to create the first entry exactly as before.
- Generic Import: it can bootstrap the entry once it has usable imported evidence and passes the normal health/snapshot validation; it remains experimental.

The first configured Gateway is called the **primary REST Gateway** only because its transport is stored in the config-entry data. That role does not imply a preferred bank or special provider status.

Supervisor supplies the private-CA trust and endpoint. The operator must still provide the Gateway bearer token and Portfolio Architect configuration directory. Portfolio Architect validates HTTPS, provider identity, health and a usable portfolio snapshot before creating the entry.

## Several Gateways discovered before first setup

All first-run discovery flows claim the same Portfolio Architect singleton unique ID. Home Assistant therefore allows only one initial Portfolio Architect Add flow to remain in progress. Other Gateway discoveries are still remembered internally by immutable `provider_id` rather than creating additional competing cards.

After the first Gateway successfully creates the canonical entry, those other discovered providers remain available under:

**Portfolio Architect → Configure → Portfolio sources → Additional REST Gateways → Add discovered REST Gateway**

The provider that created the primary entry is removed from the candidate registry when setup succeeds.

## Existing Portfolio Architect installation

Once the single Portfolio Architect config entry already exists, an installed but not-yet-configured Gateway can no longer create another top-level **Discovered → Portfolio Architect → Add** card. The discovery is retained only as an internal candidate keyed by immutable `provider_id` and can be adopted explicitly under Additional REST Gateways.

This behavior is provider-neutral. For example, if DKB is the primary Gateway, a later Comdirect discovery may be offered as a supplemental candidate. Comdirect is no longer hard-coded out of the supplemental candidate path.

The discovered path supplies endpoint/private-CA trust only. Adding the source still requires the Gateway bearer token and full verified-HTTPS, provider-identity, primary/supplemental-health and snapshot-integrity validation before the existing config-entry options are changed.

Manual **Add REST Gateway** remains available. Existing configured sources and all established HTTP→HTTPS migration, Comdirect historical→provider-qualified slug migration and trust-change refusal paths are unchanged.

## Generic Import isolation

If Generic Import is installed only for an isolated smoke or experiment, do **not** adopt it as a real production source. It may participate in provider-neutral discovery, but setup/adoption cannot complete until its canonical snapshot is healthy and usable. The isolated smoke test must not alter the real production Portfolio Architect source set; the temporary Generic Import App should be uninstalled after this standalone smoke test unless it is intentionally being adopted.

## Upgrade

1. Update the Portfolio Architect HACS integration to v1.61.1 and perform the normal Home Assistant restart.
2. Align installed official Gateway Apps to v1.61.1 for release-version consistency. Their runtime/acquisition behavior is unchanged from v1.61.0.
3. No dashboard YAML replacement is required.
4. Existing source endpoints, bearer tokens, private CA trust, acquisition methods, provider identities, plan/broker configuration and evidence remain unchanged.

## Live acceptance

For the production installation that already has one Portfolio Architect entry:

- install or start an official Gateway App that has no corresponding PA source;
- confirm no new top-level **Discovered → Portfolio Architect → Add** card remains;
- confirm **Configure → Portfolio sources → Additional REST Gateways** offers **Add discovered REST Gateway** for the unconfigured provider;
- open that path and verify it identifies the provider and endpoint and requests only its bearer token;
- back out without submitting if the Gateway is not intended to become a production source.

The provider-neutral **fresh-install** behavior is regression-covered and does not require deleting or recreating the production PA entry for live acceptance. A disposable Home Assistant instance may be used later if an end-to-end first-install UI smoke is desired.

Also confirm the existing production sources, acquisition modes/evidence, freshness, PA health and planner output remain unchanged. No authenticated DKB FinTS probing or provider-method change is part of this hotfix.
