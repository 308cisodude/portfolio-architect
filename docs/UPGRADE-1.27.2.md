# Upgrade to Portfolio Architect 1.27.2

Version 1.27.2 repairs automatic verified-HTTPS migration for an already configured
Portfolio Architect installation. It is especially important for installations that
already updated all Gateway Apps to 1.27.1 and now show a verified Home Assistant LKG
while diagnostics still report `transport_security: legacy_http`.

## Existing v1.27.1 installation with HTTPS Gateways

Leave the Gateway Apps and their App-private `/data/gateway/tls` state untouched.
Do not delete/re-add Portfolio Architect, edit `.storage`, copy CA files manually,
replace bearer tokens, or downgrade to plaintext.

1. Update **Portfolio Architect through HACS to 1.27.2**.
2. Restart Home Assistant once. The restart loads the corrected manifest/config-flow
   boundary and lets existing Supervisor discovery records reach the `hassio` flow.
3. Wait for the first Portfolio Architect evaluation. The existing primary Comdirect
   source should migrate from its matching legacy `http://...:8787/api/v1/portfolio`
   endpoint to the discovered `https://...:8787/api/v1/portfolio` endpoint only after
   the HTTPS health endpoint validates with the existing bearer token and private CA.
4. Confirm diagnostics for each migrated REST source report:
   - `transport_security: verified_https`;
   - `custom_ca_configured: true`; and
   - a populated `tls_ca_sha256`.
5. Confirm Runtime health returns to the normal live/verified state.
6. Update the installed Comdirect, Trade Republic and DKB Gateway Apps to 1.27.2 in
   place for release-version alignment. These App updates do not intentionally rotate
   the private CA or change provider runtime behavior.

Do not reauthenticate Comdirect merely because of the v1.27.2 transport migration.
If Comdirect independently requires PhotoTAN because its upstream bank session has
expired, complete that reauthentication normally. v1.27.2 does not itself require a
new Comdirect session or bearer token.

## Upgrade directly from v1.26.x

Use the same security-sensitive order as the original v1.27 design:

1. update the Portfolio Architect Home Assistant integration to 1.27.2 first;
2. restart Home Assistant;
3. update the Comdirect Gateway App in place and verify automatic HTTPS migration;
4. update Trade Republic if installed/configured and verify its migration;
5. update DKB if installed.

Never update/delete an App in a way that removes its private `/data` state.

## Single-entry behavior

The manifest-level `single_config_entry` shortcut is intentionally no longer used.
Manual **Add integration** setup still aborts whenever any Portfolio Architect entry
already exists, and the stable `portfolio_architect` unique ID remains as defense in
depth. Supervisor `hassio` discovery is the deliberate exception: it may open a flow
to migrate the one existing entry's trusted transport or to handle the already
documented provider-discovery paths. It does not create a second automatic Portfolio
Architect entry.

## No dashboard or schema migration

No dashboard YAML migration is required. Payload schema 8, REST portfolio schema 1,
Gateway health schema 6, entity IDs/unique IDs, source calculations and LKG semantics
remain unchanged.
