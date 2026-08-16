# Upgrade to Portfolio Architect 1.28.1

Version 1.28.1 changes release engineering only. It refreshes immutable GitHub
Actions to Node.js-24-capable major versions and changes no Portfolio Architect or
Gateway production behavior.

## Upgrade order

1. Update **Portfolio Architect** through HACS to 1.28.1.
2. Restart Home Assistant once and confirm the version entity reports `1.28.1`.
3. Update installed official Gateway Apps to 1.28.1 in place for version alignment.
4. Do not remove App-private data, regenerate bearer tokens or private CAs.
   **Do not reauthenticate Comdirect** solely because of this release when the current
   session is healthy.
5. Confirm configured Comdirect and Trade Republic sources return to the same healthy
   verified-HTTPS state and retain their existing CA fingerprints.
6. If the DKB App is installed, confirm it remains manual-only/non-live and retains
   the existing v1.28.0 capability-probe state.

No dashboard YAML migration is required.

## GitHub Actions maintenance

The repository's protected workflows now use:

- `actions/checkout` v7.0.1 pinned to
  `3d3c42e5aac5ba805825da76410c181273ba90b1`; and
- `actions/setup-python` v7.0.0 pinned to
  `5fda3b95a4ea91299a34e894583c3862153e4b97`.

HACS and hassfest checkout steps are updated as well, so no Portfolio Architect
workflow retains the old checkout v4.4.0 Node.js 20 action runtime. Full immutable
SHA pinning remains mandatory; mutable `@v7` tags are not used.

## DKB FinTS status unchanged

The v1.28.0 DKB research gate is unchanged. Until Portfolio Architect receives its
own FinTS product registration number, `registration_required` remains the expected
probe state. If the later anonymous probe reports `HIWPDS`, that is still only bank-level
capability evidence: there are still **no holdings** served by the DKB Gateway, and it
does not yet enable live acquisition. Authenticated user-capability/UPD
validation remains a separate gate. Version 1.28.1 does not add DKB login/PIN/TAN
handling, authenticated UPD, holdings acquisition or any write-capable banking operation.
