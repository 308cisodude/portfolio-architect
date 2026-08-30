# Upgrade to Portfolio Architect v1.61.0

v1.61.0 is a Home Assistant-side **Configure destructive-action safety and context** release. It does not change provider acquisition, Gateway wire contracts, planner economics, dashboard YAML, or the authenticated DKB FinTS research gate.

## What changes

Removing any selected configuration object is now deliberately two-step:

1. select the exact object;
2. review its immutable identity/context and explicitly confirm removal.

This applies to:

- supplemental REST Gateways — provider identity and endpoint are shown before removal;
- execution providers — provider name and immutable provider ID are shown, with an explicit reminder that nested savings-plan routes are removed with the provider and referenced funding relationships must be removed first;
- savings-plan routes — provider identity plus ISIN are shown before removal;
- funding transfers — the exact directed source-provider → destination-provider edge is shown before removal.

The existing single primary REST Gateway remains a reconfigure/edit action only. It is not offered as a removal target and cannot be implicitly replaced by removing a supplemental source.

## Upgrade

1. Update the Portfolio Architect HACS integration to v1.61.0 and restart Home Assistant normally.
2. Align installed official Gateway Apps to v1.61.0 for release-version consistency. Their runtime behavior is unchanged from v1.60.0.
3. No dashboard YAML replacement is required.
4. Existing plan, schedule, execution-provider configuration, source identities, bearer tokens, private CA trust, acquisition methods and canonical evidence remain unchanged.

## Generic Import isolation

If Generic Import is installed only for an isolated smoke or experiment, do **not** add its discovery card/source to the real production Portfolio Architect source set. This release does not change Generic Import maturity or discovery semantics; The isolated smoke test must not alter the real source set; the temporary Generic Import App should be uninstalled after this standalone smoke test unless it is intentionally being adopted.

## Live acceptance

Open **Portfolio Architect → Configure** and exercise the removal flows without confirming the final checkbox initially:

- **Portfolio sources → Additional REST Gateways → Remove REST Gateway**: selection must lead to a confirmation form showing provider ID and endpoint; no source is removed before explicit confirmation.
- **Execution providers & funding → Execution providers → Remove execution provider**: confirmation must show provider name/ID and describe the nested-route/funding-edge consequences.
- **Savings-plan routes → Remove savings-plan route**: confirmation must show provider + ISIN.
- **Funding topology → Remove funding transfer**: confirmation must show the exact directed edge.

Cancel/back out of the confirmation forms during acceptance unless a real configuration removal is intentionally desired. Confirm that the primary REST Gateway still has edit/reconfigure semantics and no remove action.

Health schema 9, schemas 1–8 compatibility, REST portfolio schema 1, Portfolio payload schema 8, config-entry schema 12, `fallback_policy: none`, evidence freshness, LKG/anti-rollback/source-set atomicity, private-PKI HTTPS, bearer authentication, DNS pinning, planner behavior and dashboard presentation remain unchanged.
