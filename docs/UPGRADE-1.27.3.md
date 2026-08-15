# Upgrade to Portfolio Architect 1.27.3

Version 1.27.3 is a narrow Home Assistant-side discovery/provider-identity hotfix. It
fixes the residual pending DKB Gateway discovery card seen after successful v1.27.2
verified-HTTPS migration when the portfolio already contains a configured DKB CSV
source.

The DKB Gateway publishes provider ID `dkb`; the CSV importer uses `dkb_csv`. Version
1.27.3 makes those namespaces explicit and applies one shared collision rule across
Supervisor discovery, discovered supplemental confirmation and manual REST Gateway
addition.

## Recommended upgrade order

1. Leave the existing v1.27.2 Portfolio Architect config entry, verified-HTTPS source
   configuration, bearer tokens and Gateway TLS state untouched.
2. Update **Portfolio Architect through HACS to 1.27.3**.
3. Restart Home Assistant once.
4. Confirm the pending **Discovered → Portfolio Architect → Add** card for the DKB
   Gateway disappears when DKB CSV is already configured.
5. Confirm diagnostics still show Comdirect and configured Trade Republic REST
   sources as `transport_security: verified_https`, `custom_ca_configured: true`,
   with the same populated `tls_ca_sha256` values as before the update.
6. Confirm Runtime health remains healthy/live and Home Assistant LKG remains
   inactive.
7. Update installed Comdirect, Trade Republic and DKB Gateway Apps to 1.27.3 in place
   for package-version alignment. Their private CA state must remain unchanged.

No dashboard YAML migration, source reconfiguration, bearer-token replacement, CA
copying, DKB CSV change, Trade Republic statement re-import, or Comdirect
reauthentication is required solely because of this release. If Comdirect independently
requires reauthentication because its upstream session expired, complete that normal
PhotoTAN flow as usual.

No dashboard YAML migration is required. Do not reauthenticate Comdirect merely because
of this v1.27.3 discovery hotfix.

## Security boundary

Removing the stray discovery card does not broaden automatic portfolio scope. A DKB
Gateway remains a distinct experimental/manual-only provider shell and is not silently
substituted for DKB CSV. The single Portfolio Architect config-entry invariant,
verified-HTTPS-before-write migration, bearer authentication, provider identity
checks, private CA trust, and no-plaintext-fallback behavior remain unchanged.
