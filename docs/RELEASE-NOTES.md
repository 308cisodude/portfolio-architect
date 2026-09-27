# Portfolio Architect v1.65.8

The DKB manual cash research path accepts a bounded printable bank system ID in its App-private, backup-excluded state. The previous ASCII-only validator rejected the live v1.65.7 capture as `non_alphanumeric`. The private JSON writer now escapes special characters and the keyed fingerprint handles UTF-8. The identifier is never shown in the admin view, logs, or Home Assistant state.

Restart-safe reuse and approval-free behavior still require one live manual acceptance trial. The 72-hour ID expiry and DKB CSV planning authority remain unchanged.

See [details](RELEASE-NOTES-1.65.8.md), the [upgrade guide](UPGRADE-1.65.8.md), and the [previous release](RELEASE-NOTES-1.65.7.md).
