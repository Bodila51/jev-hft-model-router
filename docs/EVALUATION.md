# Evaluate routing quality

Routing quality is empirical. A polished demo and a valid API response are not evidence that the system chooses correctly.

## Build a labeled scenario set

Each scenario contains:

- the natural-language request;
- optional market state;
- constraints;
- expected strategy family;
- acceptable outcome statuses.

Start with `config/evaluation_scenarios.json`, then build a private set covering your full registry.

## Minimum evaluation dimensions

- family classification accuracy;
- correct abstention when details are missing;
- correct fresh-data requirement;
- hard-filter correctness;
- top-1 and top-3 model agreement with a domain reviewer;
- confidence calibration;
- stability under paraphrases;
- stability under small, irrelevant state changes;
- sensitivity to meaningful regime and constraint changes.

## Keep a holdout set

Do not edit descriptions and policy against every labeled case. Use a development set for iteration and keep a separate holdout set for the final report.

## Compare against baselines

At minimum, compare:

1. deterministic family/regime matching;
2. the included heuristic demo backend;
3. Jev with the same registry;
4. a human reviewer where stakes justify it.

Record errors, cost, latency, abstention rate, and the version of the registry and policy used for every run.

## Claims you may make

Make only measured claims. For example:

```text
On our 120-scenario holdout set, router version X matched the labeled top-3 in Y% of cases and abstained in Z%.
```

Do not convert demo data or TypeSafe's general benchmarks into a claim about your trading router.
