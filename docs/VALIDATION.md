# v1.31.2 validation

Portfolio Architect v1.31.2 is a DKB FinTS capability-probe hardening release based on the
exact immutable v1.31.1 source baseline.

The release must prove:

- integration, engine, common Gateway and all three App versions align at `1.31.2`;
- FinTS registration input requires exactly 25 alphanumeric characters;
- the complete 25-character registration ID occurs exactly once in the anonymous FinTS
  request and specifically in `HKVVB`'s product-designation field;
- the request continues to contain only `HNHBK`, `HKIDN`, `HKVVB` and `HNHBS` and no
  holdings/order/payment-capable segment;
- registration/probe POST redirects are relative to the App root and cannot navigate the
  Ingress iframe to Home Assistant's absolute `/`;
- a valid bounded FinTS envelope with return codes but no BPD persists as `bank_rejected`;
- bounded sanitized text is retained only from recognized `HIRMG`/`HIRMS` return-message
  structures, with the configured product ID redacted and oversized text bounded;
- arbitrary/unknown segment payload and raw FinTS response bytes are never persisted;
- decoded-response SHA-256 and byte count provide non-content correlation evidence;
- protocol, transport and remote-HTTP failures persist only bounded failure metadata and do
  not revert to `ready / not probed` after reopening the App;
- previous schema-1 successful probe evidence remains loadable;
- a positive `HIWPDS` remains only bank-level research evidence and does not enable DKB
  holdings;
- DKB stays experimental, manual-only and fail-closed as a portfolio source; and
- v1.31.1 portfolio calculation/identity behavior remains unchanged.

Run the complete regression suite, strict publication/privacy checks, three independent
reproducible release builds, release verification, artifact privacy checks, and independent
Git-overlay/binary-patch replay over the exact v1.31.1 tracked baseline.

Protected GitHub workflows remain authoritative for actual provider-App Docker/private-PKI
smoke execution when local Docker is unavailable.

## Live acceptance

Upgrade all components to v1.31.2 in place, preserving DKB App-private state. Start the DKB
App manually and verify the configured registration suffix survived. Store/re-store only if
necessary and confirm the Web UI remains inside the App after POST navigation.

Run exactly one anonymous BPD probe. The decisive acceptance condition is that the resulting
state remains visible after reopening the DKB Web UI. If DKB returns a valid FinTS rejection
without BPD, the bounded return codes and sanitized bank return messages must remain visible as
`bank_rejected`; if transport or protocol processing fails, the corresponding bounded failure
state must remain visible. When a decoded FinTS payload existed, its fingerprint/byte count may
remain as correlation evidence without retaining the payload.

A successful BPD with `HIWPDS` moves only to the later authenticated user-capability/UPD
research gate. It does not enable live holdings in v1.31.2.
