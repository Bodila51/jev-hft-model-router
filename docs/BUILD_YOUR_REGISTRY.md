# Build a real model registry

The router can only choose among models it can see. A complete registry is more important than clever instructions.

## One card per independently deployable strategy

Do not create separate cards for insignificant parameter variations. Create a separate card when the strategy has a meaningfully different family, venue requirement, latency envelope, risk profile, capacity, or failure mode.

## Required evidence

Populate metrics from a reproducible pipeline:

1. backtest with fees and venue-specific constraints;
2. record in-sample and untouched out-of-sample windows;
3. run walk-forward tests;
4. stress slippage, latency, missing fills, and spread expansion;
5. record capacity assumptions;
6. version the code, data window, parameters, and result artifact;
7. mark `production_ready=true` only after independent review and paper trading.

## Avoid leakage

- Do not calculate out-of-sample metrics on a window used to tune parameters.
- Do not select the best seed and hide the rest.
- Do not omit delisted symbols or failed venues from historical data.
- Do not write strengths without corresponding known failure modes.
- Do not use Jev to invent missing metrics.

## Up to 254 candidate options

TypeSafe documents a maximum of 255 options in a `Choice`. The router reserves one for `no_trade`, leaving 254 registered choices in one decision. If more than 254 models survive hard filters, the router performs a deterministic preselection based on family, regime, horizon, and out-of-sample evidence before calling Jev.

## Import workflow

1. Copy `examples/registry-template.csv`.
2. Fill it from your evaluation database.
3. Separate list values with `|`.
4. Convert with `scripts/import_registry_csv.py`.
5. Run `jev-hft validate-registry`.
6. Review the generated JSON in Git before activating it.
