# Local REST gateway example

`portfolio.json` illustrates source schema version 1. A production gateway must
create `generated_at` from the bank snapshot it publishes and protect the
endpoint with a dedicated bearer token.

v1.5.1 includes two deployments of the same reference gateway:

- `home_assistant_app/portfolio_architect_gateway_comdirect/` for Home Assistant OS;
- `gateway/` for a separate Docker host.

Both publish `GET /api/v1/portfolio`. This fixture remains useful for contract
testing and contains no bank connector, credential, or session state.
