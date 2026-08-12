# Operations guide

## Healthy REST operation

A healthy deployment shows `Source healthy`, `Data fresh`, `Gateway status: OK`,
`Operating mode: Live`, and `Snapshot verified`.

## Gateway outage and degraded operation

After at least one successful REST evaluation, a complete Gateway outage can use
the private Home Assistant last-known-good calculation while it remains inside the
bounded retention window. Holdings, quantities, portfolio value, allocation,
architecture, and policy remain available as **informational stale data**. Runtime
health reports the degraded source and freshness continues to age from the accepted
snapshot timestamp.

Cash-based actionability is deliberately stricter. While Home Assistant LKG is
active, Gateway health is unavailable, reauthentication is required, an integrity
error is active, the source is stale, or the effective Gateway mode is not `live`,
authorized investment cash and new purchase recommendations are unavailable. Do
not treat a retained portfolio display as permission to execute a stale plan.

If the trusted cache exceeds its retention limit or no configuration-matching LKG
exists, the affected data becomes unavailable. A later valid live snapshot
automatically returns the integration to normal operation without manual cache
cleanup.

### Refresh-overdue diagnostics

`Refresh overdue` requires a current Gateway health observation that actually
proves a missed deadline. If the last health sample was taken before the scheduled
refresh plus grace, locally ticking dashboard entities may show `due_now`, but they
do not escalate that old sample into an overdue failure. The next normal health
observation can confirm either the successful refresh or a real miss.

`Snapshot age` and `Snapshot expires in` are calculated from the accepted snapshot
timestamp and update locally once per minute. They do not cause additional bank or
portfolio API calls.

## Backups

Create a versioned backup before an integration upgrade:

```bash
./tools/create_backup.sh
```

Backup retention is dry-run by default:

```bash
./tools/prune_backups.sh --keep 5
./tools/prune_backups.sh --keep 5 --apply
```

## Rollback

Restore a named backup and validate Home Assistant before restarting:

```bash
./tools/rollback_home_assistant.sh /config/portfolio-architect-backups/<backup>
ha core restart
```

The rollback helper creates an additional safety backup before replacing files.
It does not modify Gateway App-private data.

## Cost-aware execution

Cost-aware execution is opt-in under **Portfolio Architect → Configure →
Execution policy**. Existing installations continue to use the legacy
recommendation behaviour until it is enabled.

For the Comdirect live-reserve path:

1. Open the Portfolio Architect Gateway App Web UI.
2. Complete PhotoTAN reauthentication when required.
3. Discover the bounded list of eligible EUR accounts.
4. Select the masked dedicated investment/settlement account explicitly.
5. Review the Gateway **Investment cash authorization** policy.
6. Reload Portfolio Architect and enable `gateway_balance` reserve mode.

The Gateway never guesses the settlement account. If the selected account is
missing, ambiguous, non-EUR, or lacks both booked-balance and available-cash
values, the reserve is unavailable and cost-aware recommendations fail closed.

The Gateway first derives eligible cash as the lower of booked balance and
available cash. This prevents an overdraft or credit facility from being treated
as investable money and prevents pending debits from being ignored. It then
applies the configured authorization policy. `all_available` preserves the full
eligible amount; `capped` limits the amount Portfolio Architect may allocate.

When the live source is unavailable, Home Assistant may continue to display the
validated last-known-good portfolio. Do not execute a cost-aware recommendation
until `Source healthy` and the authorized-investment-cash timestamp are current again.

Savings-plan rates are treated as gross cash. A paid percentage savings plan
therefore reduces the investable principal so principal plus fee does not exceed
the configured reserve. Manual-order recommendations likewise reserve cash for
estimated fees in addition to the order principal.


### v1.20.1 LKG propagation

When a live REST cycle falls back to the Home Assistant last-known-good calculation, Portfolio Architect still completes the coordinator cycle and notifies entities even if the retained portfolio calculation itself is unchanged. Informational holdings may remain available, while authorized cash and recommendation-derived entities immediately become unavailable until live actionability returns. Integrity Repairs represent integrity evidence from the current refresh path and are not carried into an unrelated transport/calculation fallback.
