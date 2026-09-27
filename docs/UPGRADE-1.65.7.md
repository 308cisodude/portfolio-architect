# Upgrade to v1.65.7

Update the Portfolio Architect integration and all four version-aligned Gateway Apps. No dashboard YAML replacement is needed. Existing DKB cash/holdings shadows and private system-ID/key files survive an in-place upgrade. Both private files remain excluded from HA backups.

Make one manual read-only DKB cash observation and complete bank approval if requested. Record only the bounded `capture reason` together with load/capture/save outcomes. If capture remains invalid, stop: do not restart the App or repeat the 25-hour trial. The category determines whether further protocol research or a narrow validator change is justified. Do not share the ID, raw response, credentials, or balance. CSV planning is unchanged.
