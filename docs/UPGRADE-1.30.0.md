# Upgrade to Portfolio Architect 1.30.0

Version 1.30.0 adds provider-aware execution-policy planning and route-scoped accepted
exceptions. It does not change provider acquisition or Gateway wire/network behavior.

## Safe upgrade order

1. Update **Portfolio Architect** through HACS to 1.30.0.
2. Restart Home Assistant once.
3. Update installed **Comdirect**, **Trade Republic** and **DKB** Gateway Apps to
   1.30.0 in place for package alignment.
4. Do not delete App-private data, replace bearer tokens or regenerate private CAs.
   Do not reauthenticate Comdirect solely because of this release.
5. Confirm configured REST sources retain verified HTTPS and their existing CA
   fingerprints.
6. Confirm DKB remains `registration_required` unless the project FinTS registration
   number has subsequently been issued and configured deliberately.
   The v1.28 FinTS gate is unchanged: a later positive `HIWPDS` BPD result is only
   bank-level evidence. Authenticated user-capability/UPD validation is still required,
   and v1.30 performs no holdings acquisition through DKB FinTS.

No dashboard YAML migration is required for runtime compatibility. The reference dashboard
is user-owned after import; users who want execution-provider names and the new
exception-review Tile must deliberately import the v1.30 reference or merge the
changes into their existing dashboard.

## Existing single-broker installations

No broker configuration migration is required.

A schema-1 `broker.yaml` continues to mean one execution provider and preserves the
pre-v1.30 behavior. The current public example therefore remains operational without
adding a second provider.

The current Robotics exception is migrated to exceptions schema 2 with this assumption:

```yaml
assumptions:
  preferred_execution_provider: comdirect
```

With the existing single-Comdirect broker configuration that assumption still holds,
so the expected post-upgrade state remains **accepted exception**, not review required.

## Enabling provider-aware routing

Provider-aware routing is an explicit configuration change. Convert `broker.yaml` to
schema 2 only after you have independently verified the fee data for every provider you
intend PA to consider.

Schema 2 requires:

- `fee_data_max_age_days`;
- a bounded `providers` map;
- provider `name`, `source` and `as_of` evidence; and
- the relevant savings-plan/manual-order fee data.

See `docs/EXECUTION-PROVIDERS.md` for the full format.

PA does not infer current Trade Republic, Comdirect or other broker pricing from the
provider name, holdings source or historical transactions. A provider is eligible only
from the explicit configured evidence, and stale evidence is excluded from route and
fee-policy decisions.

## Robotics acceptance scenario

The primary v1.30 acceptance scenario deliberately mirrors the governance problem that
motivated the release:

1. The Robotics distributing share class has an accepted `accumulating_preferred`
   exception whose original route assumption is Comdirect.
2. Configure a second **synthetic/test or independently verified live** execution
   provider route for the Robotics ISIN that is economically preferable to Comdirect.
3. Re-evaluate the plan.
4. Confirm the Robotics exception changes from `accepted_exception` to
   `review_required`.
5. Confirm the accepted-exception count decreases accordingly and the policy warning
   becomes active pending a new decision.
6. Confirm the exception detail retains the old decision date and reports the expected
   and newly preferred provider IDs.
7. Confirm **Next review** no longer displays the old future date for that invalidated
   assumption.
8. Confirm a purchase recommendation, when Robotics is selected for purchase, exposes
   the preferred execution provider and fee-data date.

The correct governance action after that signal is human review: confirm whether the
new provider route removes the need for the old exception, changes its rationale, or
should become only a documented fallback. PA does not silently rewrite policy.

## Compatibility and safety

- payload schema 8 remains unchanged; provider recommendation fields are optional
- REST portfolio schema 1 remains unchanged
- Gateway health schema 6 remains unchanged
- existing entity IDs/unique IDs remain unchanged
- the new exception-review count and provider attributes are additive
- portfolio-source aggregation/LKG behavior remains unchanged
- DKB live holdings remain disabled pending the existing registration/authenticated
  capability gates
- no trading, order placement, transfer, payment or transaction-history operation is
  added

The historical `v1.19.0-rc2` brokerage probe remains excluded and is not revived by
provider-aware planning.
