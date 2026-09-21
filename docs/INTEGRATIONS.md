# Connect a chat or agent

The router has three interfaces. All return the same `RouteResponse` and never execute trades.

## HTTP

Start the server with `jev-hft serve`, then call `POST /v1/route`.

The calling chat or agent must:

1. preserve the user's original request in `query`;
2. collect or fetch missing market state;
3. pass explicit capital, latency, venue, drawdown, and risk limits under `constraints`;
4. never fabricate market data;
5. show `no_trade` and `review_required` without overriding them;
6. describe the result as best-fit **within the connected registry**;
7. never translate the response into an automatic order.

Use `examples/openai-tool-schema.json` as a starting function definition. Point the tool implementation to the local HTTP endpoint.

## MCP

Install the optional extra:

```bash
pip install -e ".[mcp]"
```

The command `jev-hft-mcp` exposes `recommend_hft_model`. It accepts:

- `query`: the original natural-language request;
- `market_json`: a JSON string containing normalized market state;
- `constraints_json`: a JSON string containing user and infrastructure limits.

Adapt `examples/mcp-config.json` to the absolute repository path and store the TypeSafe key using the agent's secret-management mechanism.

## Built-in browser chat

`jev-hft serve` also serves a small local interface at `http://127.0.0.1:8000`. It is intended for setup checks and demonstrations, not authentication or public hosting.

## System instruction for a calling agent

```text
Use recommend_hft_model only to select among the connected strategy registry.
Before calling it, obtain the user's goal and any required market snapshot,
venue, symbol, capital, latency, drawdown and risk constraints. Never invent
missing live data. Preserve NO_TRADE and REVIEW_REQUIRED outcomes. Never claim
that the selected strategy is profitable or execute an order.
```
