# Portfolio Architect Gateway v1.17.1

The v1.17.1 App package retains the v1.16.0 Gateway runtime unchanged.

This release adds the optional investment-reserve path used by Portfolio
Architect's cost-aware execution engine.

After completing or refreshing Comdirect authentication, open the App Web UI:

1. select **Discover investment accounts**;
2. review the bounded masked EUR-account choices;
3. select the dedicated investment/settlement account explicitly;
4. wait for the next successful portfolio refresh.

The Gateway requires both booked balance and available cash for the selected
account. It publishes the lower non-negative value, preventing overdraft or
pending-debit money from being treated as investable cash. If the semantics are
incomplete, the reserve is omitted and Portfolio Architect fails closed.

The update preserves App-private API credentials, OAuth/session state, Gateway
bearer token, cached snapshot, and selected account. Never uninstall the App or
remove its data for a normal update.

The selected live Comdirect account balance semantics were validated before the
v1.17.1 publication milestone. The Gateway remains GET-only and contains no
trading, transfer, payment, or transaction-history operation.
