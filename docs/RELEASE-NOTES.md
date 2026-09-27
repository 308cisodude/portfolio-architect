# Portfolio Architect v1.65.7

The DKB manual cash research page now explains why a transient bank system ID was rejected by the existing strict storage gate. It reports only a fixed category: absent, zero sentinel, non-string, empty, over-limit, non-alphanumeric, or valid. No ID value, character, length, type name, credential, or raw response is rendered or logged. The keyed fingerprint remains unavailable when capture fails.

This follows v1.65.6 live evidence: the cash read succeeded, but ID capture was invalid and persistence was skipped. The category will guide a narrowly scoped correction if the bank provides a reusable ID in a shape the current gate does not accept. No acceptance of restart-safe reuse is claimed. DKB CSV remains authoritative for planning.

See [details](RELEASE-NOTES-1.65.7.md), the [upgrade guide](UPGRADE-1.65.7.md), and the [previous release](RELEASE-NOTES-1.65.6.md).
