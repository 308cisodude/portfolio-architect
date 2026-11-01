# Upgrade to v1.66.2

Update the integration and the four version-aligned Gateway Apps. Replace the reference dashboard YAML with the v1.66.2 English, German or combined artifact. No configuration migration, source refresh or bank approval is needed for the presentation change.

In the PA dashboard's Runtime health section, the **Instrument types** tile should show **2 unspecified types** (or **2 unbekannte Typangaben**) for the October 17 cached observations, while the two ISINs remain available in the tile detail. The count is informational; it does not indicate an identity collision or block the ready plan.

If DKB FinTS has expired, the plan remains blocked. The dashboard should now name DKB as the current unavailable Gateway and mark the old TR date as part of the retained calculation. Refresh DKB holdings and cash manually when you want planning restored; PA then needs a successful read of all sources to accept the newer TR statements. Verify FinTS authority, no automatic fallback and the EUR 0 DKB cash cap remain set.

The pending v1.66.1 DKB transient review label can be checked during that ordinary manual read. This release changes no planning or acquisition behavior.

Rollback to v1.66.1 restores the previous diagnostic wording. The underlying source metadata and all authority settings remain compatible. Consult the [v1.66.1 upgrade guide](UPGRADE-1.66.1.md) for its earlier presentation change.
