# Upgrade to Portfolio Architect v1.62.3

v1.62.3 is a narrow Trade Republic cash-statement compatibility hotfix on top of v1.62.2. It preserves the integration-owned first-run lifecycle and explicit-choice safety while making `KONTOAUSZUG` cash-date parsing complete for the bounded German abbreviated month-label matrix used by locale-aware provider documents.

## Why this patch exists

A current native Trade Republic cash statement rendered the authoritative cash as-of line as `Zum 02 Sept. 2026`. The v1.62.2 parser recognized only three-letter tokens followed by a period, so the statement failed. Reviewing the complete German abbreviated month set showed that a September-only exception would still leave predictable failures for `März`, `Mai`, `Juni` and `Juli`, whose conventional abbreviated labels are not all three letters and do not all use a trailing period.

v1.62.3 therefore accepts this explicit German matrix:

`Jan.`, `Feb.`, `März`, `Apr.`, `Mai`, `Juni`, `Juli`, `Aug.`, `Sept.`, `Okt.`, `Nov.`, `Dez.`

The parser also preserves aliases accepted before v1.62.3: `Mär.`, `Mar.`, `Mai.`, `May.`, `Jun.`, `Jul.`, `Sep.`, `Oct.` and `Dec.`. It does not accept arbitrary other four-letter/full-month spellings.

The patch also separates the missing/unsupported-date error from true multi-date ambiguity.

## Existing installations

No configuration migration is required. Config-entry schema 13, source configuration, broker configuration, provider identities, private CA fingerprints, bearer tokens, Generic profiles and freshness thresholds remain unchanged.

For an established installation:

1. update the Portfolio Architect integration to v1.62.3 and restart Home Assistant once;
2. align the installed provider Gateway Apps to v1.62.3;
3. preserve all App-private state and existing imported evidence;
4. re-import the previously rejected current Trade Republic `KONTOAUSZUG` through the normal **Investment cash** control;
5. confirm the import is accepted and the Trade Republic cash evidence timestamp advances while holdings evidence remains independent.

The rejected earlier import did not replace the prior accepted cash snapshot, so no recovery or manual state repair is required.

## Trade Republic parser boundaries

The parser remains deliberately strict:

- only the explicit German month-label matrix above plus pre-existing compatibility aliases are accepted;
- cash evidence must still contain exactly one supported `BARMITTELÜBERSICHT` as-of date;
- Cashkonto opening/incoming/outgoing/ending arithmetic must reconcile;
- trust-account and money-market-fund custody components must reconcile to the ending Cashkonto balance;
- creation timestamp and as-of chronology remain validated;
- unsupported, scanned/image-only, encrypted, ambiguous or inconsistent statements continue to fail closed;
- uploaded PDF bytes and transaction-level/private identity data are not persisted.

## v1.62.2 first-run behavior

The v1.62.2 explicit first-run choices and Generic READY-profile colour behavior are unchanged. An LG clean-room fixture already in `plan_required` can be updated directly to v1.62.3 and used to finish the v1.62.2 live acceptance without recreating the Portfolio Architect service or Generic profile.

## Planned live acceptance

Production / Trade Republic:

1. update the integration and Trade Republic Gateway to v1.62.3 without clearing private state;
2. import the same current native cash statement that the previous parser rejected;
3. confirm it is accepted with an advanced cash evidence timestamp;
4. confirm the already accepted current holdings snapshot is unchanged;
5. confirm source freshness/actionability stays healthy once all required evidence is within policy;
6. align Comdirect and DKB to v1.62.3 for package-version hygiene and confirm planner/source economics remain unchanged.

LG clean-room:

1. update PA and Generic Import directly to v1.62.3;
2. preserve the existing single PA service, `plan_required` state and Generic provider identity;
3. reopen **Complete initial setup** and confirm all first-run target/numeric/enumeration/Yes-No fields begin genuinely unanswered;
4. complete the synthetic setup only with explicit choices and confirm normal runtime begins only after successful staged validation;
5. confirm READY Generic source-profile presentation is blue while active/authoritative CSV remains green.
