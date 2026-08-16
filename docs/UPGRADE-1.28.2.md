# Upgrade to Portfolio Architect 1.28.2

Version 1.28.2 changes repository dependency automation only. It groups GitHub
Actions Dependabot **version updates** into one reviewed pull request per update
cycle. Portfolio Architect integration and Gateway production behavior are unchanged.

## Upgrade order

1. Update **Portfolio Architect** through HACS to 1.28.2.
2. Restart Home Assistant once and confirm the version entity reports `1.28.2`.
3. Update installed official Gateway Apps to 1.28.2 in place for version alignment.
4. Do not remove App-private data, regenerate bearer tokens or private CAs.
   **Do not reauthenticate Comdirect** solely because of this release when the current
   session is healthy.
5. Confirm configured Comdirect and Trade Republic sources return to the same healthy
   verified-HTTPS state and retain their existing CA fingerprints.
6. If the DKB App is installed, confirm it remains manual-only/non-live and retains
   the existing v1.28.0 capability-probe state.

No dashboard YAML migration is required.

## Dependabot grouping

The `github-actions` Dependabot configuration remains weekly with a five-open-PR
limit. All GitHub Actions version updates now match one group:

```yaml
groups:
  github-actions-version-updates:
    applies-to: version-updates
    patterns:
      - "*"
```

This release deliberately does **not** add a `security-updates` group. The grouping
policy therefore applies to ordinary GitHub Actions version updates, while security
update handling is not coupled to that batch.

The workflow action pins themselves are unchanged from v1.28.1 and remain immutable
full commit SHAs.

## DKB FinTS status unchanged

The v1.28.0 DKB research gate is unchanged. Until Portfolio Architect receives its
own FinTS product registration number, `registration_required` remains the expected
probe state. If the later anonymous probe reports `HIWPDS`, that is still only
bank-level capability evidence: there are still **no holdings** served by the DKB
Gateway, and it does not enable live acquisition. Authenticated user-capability/UPD
validation remains a separate gate. Version 1.28.2 does not add DKB login/PIN/TAN
handling, authenticated UPD, holdings acquisition or any write-capable banking
operation.
