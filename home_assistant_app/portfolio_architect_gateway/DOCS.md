# Portfolio Architect Gateway v1.21.0

Version 1.21.0 aligns this App package with Portfolio Architect's execution-semantics release. Gateway banking behavior and wire contracts remain unchanged from 1.20.1. Existing cash authorization, bootstrap, account-selection, and cached-snapshot behavior are retained.

After completing or refreshing Comdirect authentication, open the App Web UI:

1. select **Discover eligible EUR accounts**;
2. review the bounded masked choices;
3. select the dedicated investment/settlement account explicitly;
4. review **Investment cash authorization**;
5. keep **All eligible cash** or choose **Cap eligible cash** and enter the EUR cap;
6. wait for the live portfolio refresh.

The Gateway first requires both booked balance and available cash and uses the
lower non-negative amount as **eligible cash**. It then applies the authorization
policy. Portfolio Architect receives the authorized amount through the existing
reserve field plus additive explanatory cash metadata.

The default `all_available` policy requires no migration action and preserves the
behavior of existing installations. A stale cap submitted while switching back to
`all_available` is discarded server-side and never persisted. A capped policy with
missing or malformed cap state still fails closed.

The update preserves App-private API credentials, OAuth/session state, Gateway
bearer token, cached snapshot, selected account, and cash policy. Never uninstall
the App or remove its data for a normal update.

The Gateway remains GET-only and contains no trading, transfer, payment, or
transaction-history operation.
