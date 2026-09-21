# Jev HFT Model Router

Turn one natural-language trading request into a confidence-gated selection from a registry of up to 254 user-owned strategy models.

```text
USER REQUEST + MARKET STATE + CONSTRAINTS
                    ↓
          JEV CLASSIFIES THE TASK
                    ↓
        CODE REMOVES INCOMPATIBLE MODELS
                    ↓
      JEV CHOOSES A REGISTERED MODEL
                    ↓
        CONFIDENCE / NO-TRADE GATE
                    ↓
            PAPER TEST REQUIRED
```

The repository includes:

- a real TypeSafe/Jev backend;
- an offline deterministic demo backend;
- exactly 200 synthetic model cards for an immediate demo;
- a terminal chat;
- a local browser chat;
- a universal HTTP API;
- an optional MCP tool for compatible agents;
- confidence and fresh-data gates;
- a labeled evaluation harness;
- an append-only audit log without raw prompt storage;
- **no order placement or live trading code**.

> [!IMPORTANT]
> The included 200 profiles are synthetic and are clearly marked `synthetic-demo`. They prove the routing system works, but they are not real strategies or performance claims. Replace them with your own model cards before evaluating financial usefulness.

## What Jev does—and does not do

Jev receives structured state and answers narrow typed questions with `Choice`, `Score`, and `Noul`. The router uses Jev to classify intent, identify when live data is required, choose among compatible registered models, and abstain when the evidence is insufficient.

Jev does **not**:

- invent trading strategies;
- calculate deterministic backtest metrics;
- know every proprietary HFT model in existence;
- guarantee that the selected model will be profitable;
- execute orders.

Exact math, risk limits, venue compatibility, capital limits, and latency constraints remain ordinary code. This follows TypeSafe's documented pattern: use atomic typed judgments, then compose them with rules in code.

Official references: [TypeSafe introduction](https://docs.typesafe.ai/introduction), [quick start](https://docs.typesafe.ai/introduction/quickstart), [primitives](https://docs.typesafe.ai/primitives), [Choice](https://docs.typesafe.ai/primitives/choice), and [confidence](https://docs.typesafe.ai/confidence).

## 1. Install from zero

Python 3.10 or newer is required.

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -e ".[mcp]"
```

Copy the environment template:

```bash
# macOS / Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Create a TypeSafe key at [console.typesafe.ai](https://console.typesafe.ai/) and place it in `.env`:

```env
TYPESAFE_API_KEY=your-local-key
JEV_HFT_BACKEND=jev
```

Never commit `.env` or put the API key in a browser bundle.

## 2. Prove the repository works offline

The offline backend is a deterministic smoke-test. It is not Jev and identifies itself as `heuristic-demo` in every response.

```bash
JEV_HFT_BACKEND=heuristic jev-hft validate-registry

JEV_HFT_BACKEND=heuristic jev-hft route \
  "Find a low-risk market-making model for BTC in a range-bound market" \
  --constraints '{"asset_class":"crypto","symbol":"BTC-USDT","capital_usd":100000,"available_latency_ms":1,"max_risk_level":3}'
```

Expected properties:

- `scanned_models` is `200`;
- the classified family is `market_making`;
- the backend is `heuristic-demo`;
- `execution_allowed` is always `false`;
- the selected demo profile includes `MODEL_NOT_MARKED_PRODUCTION_READY`.

## 3. Route with real Jev

Set the key and backend in `.env`, then run the same command:

```bash
jev-hft route \
  "Find a low-risk market-making model for BTC in a range-bound market" \
  --constraints '{"asset_class":"crypto","symbol":"BTC-USDT","venue":"binance","capital_usd":100000,"available_latency_ms":1,"max_drawdown":0.12,"max_risk_level":3}'
```

The router makes two Jev decisions:

1. classify the request into a family, horizon, regime, risk level, live-data need, and abstention probability;
2. use one high-cardinality `Choice` to select from every model that survives deterministic constraints, plus `no_trade`.

TypeSafe documents up to 255 options for a `Choice`. This repository reserves one option for `no_trade`, so the configured maximum is 254.

## 4. Start the chat

Terminal chat:

```bash
jev-hft chat
```

Inside the chat, set structured context before a live request:

```text
/market {"asset_class":"crypto","symbol":"BTC-USDT","venue":"binance","regime":"range_bound","spread_bps":1.4,"observed_latency_ms":0.8}
/constraints {"capital_usd":100000,"available_latency_ms":1,"max_drawdown":0.12,"max_risk_level":3}
Find the best-fit market-making model for this state.
```

Browser chat and API:

```bash
jev-hft serve
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Interactive API docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Docker alternative:

```bash
docker compose up --build
```

The compose file publishes the service only on local `127.0.0.1:8000`.

## 5. Connect any chat or agent

Any system capable of calling HTTP can use:

```http
POST http://127.0.0.1:8000/v1/route
Content-Type: application/json
```

```bash
curl -X POST http://127.0.0.1:8000/v1/route \
  -H "Content-Type: application/json" \
  --data @examples/request.json
```

Use `examples/openai-tool-schema.json` to expose the endpoint as a function tool. The calling agent should collect missing market state and constraints before invoking the router.

For MCP-compatible agents:

```bash
pip install -e ".[mcp]"
jev-hft-mcp
```

Copy and adapt `examples/mcp-config.json`. Use absolute paths for the registry and policy files.

See [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) for the required agent behavior.

## 6. Teach the router about your models

There is no fine-tuning step. You teach the system by providing factual, versioned model cards and labeled routing scenarios.

Start from `examples/registry-template.csv`. Add one row per strategy using evidence from your own backtests and deployment constraints, then convert it:

```bash
python scripts/import_registry_csv.py \
  examples/registry-template.csv \
  config/model_registry.json
```

Validate it:

```bash
JEV_HFT_REGISTRY=config/model_registry.json \
  jev-hft validate-registry
```

Activate it in `.env`:

```env
JEV_HFT_REGISTRY=config/model_registry.json
```

A useful model card needs:

- a unique id and plain-language description;
- strategy family;
- supported assets, symbols, venues, horizons, and regimes;
- minimum capital and maximum acceptable latency;
- risk level and live-order-book requirement;
- strengths and known failure modes;
- out-of-sample evidence, drawdown, slippage, capacity, and walk-forward results;
- `source` and `production_ready` provenance fields.

Read [docs/BUILD_YOUR_REGISTRY.md](docs/BUILD_YOUR_REGISTRY.md) before marking a model production-ready.

## 7. Supply fresh market state

When Jev determines that a request depends on current conditions, the router requires a fresh `market` object. The default maximum age is 30 seconds.

```json
{
  "timestamp": "2026-09-21T20:30:00Z",
  "asset_class": "crypto",
  "symbol": "BTC-USDT",
  "venue": "binance",
  "regime": "range_bound",
  "volatility_percentile": 0.31,
  "spread_bps": 1.4,
  "order_book_depth_usd": 5200000,
  "volume_24h_usd": 18000000000,
  "funding_rate": 0.0001,
  "observed_latency_ms": 2.1,
  "source": "your-market-data-adapter"
}
```

This repository intentionally does not pretend a free REST ticker is HFT-grade market data. Connect your own authorized feed or agent tool and pass the normalized snapshot into `/v1/route`.

If live data is required but missing or stale, the result is `no_trade` with `FRESH_MARKET_DATA_REQUIRED`.

## 8. Configure safety and confidence

Edit `config/policy.json`:

```json
{
  "min_selection_confidence": 0.45,
  "max_abstain_probability": 0.65,
  "live_data_requirement_threshold": 0.55,
  "max_market_data_age_seconds": 30,
  "max_choice_options": 254,
  "alternative_count": 3,
  "include_no_trade_option": true
}
```

Three independent gates exist:

1. Jev may classify the request as too ambiguous.
2. Code may eliminate every incompatible model.
3. Jev may choose `no_trade` or return confidence below the required threshold.

The response then becomes `no_trade` or `review_required`; it never silently forces a recommendation.

## 9. Evaluate before claiming quality

Run the included smoke scenarios:

```bash
JEV_HFT_BACKEND=heuristic jev-hft evaluate
```

Then replace `config/evaluation_scenarios.json` with at least 50–100 decisions labeled by someone who understands your strategies. Include:

- obvious matches;
- ambiguous requests;
- missing-data cases;
- incompatible capital and latency;
- regimes where the correct answer is `no_trade`;
- models with attractive in-sample performance but weak out-of-sample evidence.

Run the evaluation with `JEV_HFT_BACKEND=jev`, inspect disagreements, improve model cards or policy, and rerun. Do not tune against one scenario and call it production-ready.

Read [docs/EVALUATION.md](docs/EVALUATION.md).

## 10. Production boundary

Before any real-world use, keep the selected model behind:

```text
JEV ROUTE
→ HOLDOUT REPLAY
→ FEE / SLIPPAGE STRESS
→ PAPER TRADING
→ HUMAN RISK APPROVAL
→ SEPARATE EXECUTION SYSTEM
```

This repository ends at the recommendation. It deliberately has no broker keys, exchange keys, order endpoints, or automatic execution path.

## Repository layout

```text
config/                 model registry, policy, labeled scenarios
docs/                   integration, registry, evaluation, security guides
examples/               request payloads and agent tool schemas
scripts/                demo generator and CSV importer
src/jev_hft_router/     core package, API, CLI, MCP and browser chat
tests/                  offline routing and guardrail tests
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

The test suite does not call Jev or require an API key. Use the evaluation harness for live Jev checks.

## License

MIT. See [LICENSE](LICENSE).

## Risk notice

This project is research infrastructure, not financial advice, a fiduciary service, or a trading system. Model selection is limited to the registry and evidence you provide. Historical and simulated performance do not establish future profitability.
