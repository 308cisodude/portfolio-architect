# Portfolio Architect 1.18.1

Version 1.18.1 is a stable maintenance release focused on holding observability and
clearer dashboard terminology. It is based directly on the v1.18.0 stable baseline.

## Holding quantity observability

- Adds one `holding_quantity` sensor for every whole-portfolio holding.
- Carries exact provider-supplied quantities through the provider-neutral position and
  holding model.
- Comdirect Gateway snapshots expose the optional quantity returned by the position
  source; DKB CSV imports retain the existing `Stückzahl` value.
- Multi-depot and multi-source quantities are summed only when every contributing
  component provides a quantity. If evidence is incomplete, quantity is deliberately
  unavailable rather than inferred.
- REST portfolio schema 1 remains backward compatible: `quantity` is optional.

## Dashboard terminology

- Renames **Complete portfolio** to **Total portfolio value**.
- Renames **Current plan drift** to **Current portfolio allocation**.
- Applies equivalent German wording: **Gesamtportfoliowert** and
  **Aktuelle Portfolioallokation**.

## Stability boundary

- Payload schema 8, REST schema 1, Gateway health schema 5, recommendation logic,
  target corridor, policy semantics, execution-cost model, reserve logic, Plan Delta
  semantics, and existing entity IDs are unchanged.
- No transaction history is introduced and Portfolio Architect does not infer that a
  quantity change represents an executed recommendation.
- The experimental v1.19.0 brokerage-diagnostic work is not included.
