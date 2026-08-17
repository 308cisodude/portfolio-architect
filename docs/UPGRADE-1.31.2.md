# Upgrade to Portfolio Architect 1.31.2

Version 1.31.2 is a narrow DKB FinTS capability-probe hardening release prepared from
immutable v1.31.1 after the first live registered probe reached DKB over verified HTTPS
but exposed three provider-App UX/diagnostic gaps.

The live v1.31.1 attempt proved that the DKB App could store the project's newly issued
registration identity and reach the fixed DKB FinTS endpoint. The attempt then ended in
`ProtocolError`; because failed probe evidence was not persisted, reopening the App
incorrectly returned to `ready / not probed`. Both the registration and probe POSTs also
redirected to absolute `/`, which let Home Assistant's root dashboard appear inside the
Ingress iframe.

Version 1.31.2 fixes those defects without enabling DKB portfolio acquisition.

## Upgrade order

1. Update **Portfolio Architect** through HACS to 1.31.2 and restart Home Assistant once.
2. Update **Portfolio Architect Gateway — Comdirect** and **Portfolio Architect Gateway —
   Trade Republic** in place for package alignment. Their runtime behavior is unchanged.
3. Update **Portfolio Architect Gateway — DKB** in place. Do not remove App-private data.
   The existing private TLS state, bearer token, and configured FinTS registration number
   are retained.
4. Start the DKB App manually and open its Web UI. Confirm the configured-registration
   suffix still matches the issued registration number.
5. Do not add the DKB Gateway as a Portfolio Architect source. It remains experimental,
   manual-only and non-live.

No dashboard YAML migration is required. No portfolio-plan migration or bank-authentication migration is required by v1.31.2.

Do not reauthenticate Comdirect solely because of this release when the current session is healthy. Do not recreate Trade Republic or DKB sources, replace bearer tokens, or change private-CA trust merely for the v1.31.2 probe hardening.

## Exact FinTS product-registration contract

The FinTS registration notice requires the complete **25-character registration ID** to
be transmitted exclusively in the **Produktbezeichnung** field of segment `HKVVB`.
Version 1.31.2 therefore requires exactly 25 alphanumeric characters at both the Web UI
and wire-validation boundaries.

The anonymous request remains limited to:

- `HNHBK`;
- `HKIDN`;
- `HKVVB`; and
- `HNHBS`.

The configured 25-character registration ID occurs exactly once in the request, in the
`HKVVB` product-designation field. The separate bounded FinTS product-version field is
unchanged. No DKB login name, PIN or TAN is sent, and the anonymous probe sends no holdings request, balance request, transaction, order, transfer, payment or debit business transaction.

## Ingress-safe navigation

POST/Redirect/GET navigation now uses a relative App-root redirect rather than absolute
`/`. Storing the registration number or running the probe therefore returns to the DKB
App inside its Home Assistant Ingress namespace instead of navigating the iframe to the
Home Assistant root dashboard.

## Sanitized persistent probe outcomes

Successful probe evidence remains bounded to BPD version, observed parameter-segment
identifiers, four-digit FinTS return codes, bounded sanitized `HIRMG`/`HIRMS` message text,
timestamp, decoded-response SHA-256/byte count and whether `HIWPDS` is advertised.
Raw FinTS response content is still discarded.

Version 1.31.2 extends the persisted probe-state schema so an expected failed attempt no
longer disappears when the Web UI is reopened. The App can now distinguish:

- `complete` — BPD was supplied and normal capability interpretation is possible;
- `bank_rejected` — a syntactically valid bounded FinTS response supplied return codes but
  no BPD;
- `remote_http_error` — the fixed DKB endpoint returned a non-success HTTP status;
- `transport_error` — no usable FinTS response was obtained because transport failed;
- `protocol_error` — a response failed the strict bounded FinTS parser; and
- bounded internal failure states for unexpected Gateway/App failures.

A valid FinTS envelope with `HIRMG`/`HIRMS` return codes but no `HIBPA` is retained as
`bank_rejected` instead of being discarded as a generic protocol error. Bounded four-digit
return codes and only their recognized `HIRMG`/`HIRMS` operator-message text survive. The
configured product registration is redacted if echoed, message text is strictly bounded, and
arbitrary/unknown segment payload remains discarded. A SHA-256 and byte count of the decoded
FinTS response are retained for correlation; the raw response itself is not persisted.

The App does **not** guess that `bank_rejected` means the new registration has not yet
propagated. The UI states only that delayed propagation is one possible cause. The return
codes remain the authoritative sanitized evidence until a documented interpretation is
available.

## Retrying the first registered probe

After upgrade:

1. confirm the stored registration suffix is correct;
2. confirm the Web UI remains inside the DKB App after any configuration POST;
3. run **Probe DKB FinTS capabilities** once;
4. record only state, BPD version, `HIWPDS` advertisement, observed parameter segments,
   bounded return codes, sanitized bank return messages, decoded-response fingerprint/size,
   and any bounded HTTP/failure category shown by the App; and
5. do not repeatedly retry an inconclusive result.

Interpretation remains unchanged. A positive bank-level result still requires an authenticated user capability/UPD gate before any holdings implementation:

- `HIWPDS: yes` is bank-level evidence only and moves research to the later authenticated
  user capability/UPD and DKB decoupled-authentication gate;
- `HIWPDS: no` stops the live FinTS-holdings branch unless another supported read-only
  acquisition design is identified; and
- any rejection/error state is inconclusive capability evidence and does not enable DKB
  holdings.

## Preserved boundaries

- payload schema 8: unchanged
- REST portfolio schema 1: unchanged
- Gateway health schema 6: unchanged; schemas 1–5 remain supported
- v1.31 canonical accumulating Robotics target and v1.31.1 ISIN-only hotfix: unchanged
- Comdirect acquisition/OAuth/session behavior: unchanged
- Trade Republic statement import/private snapshot behavior: unchanged
- private-PKI verified HTTPS, bearer authentication, Supervisor trust discovery, DNS
  pinning and no-plaintext fallback: unchanged
- DKB provider identity `dkb` remains separate from DKB CSV identity `dkb_csv`
- DKB remains experimental, manual-only, fail-closed and non-live
- no trading, order, automatic sell, transfer, payment or transaction-history capability
