# Repository instructions for coding agents

- Jev is a typed decision layer, not a trading executor or text generator.
- Keep exact math and hard safety constraints in ordinary code.
- Preserve `no_trade`, confidence gates, and `execution_allowed=false`.
- Never add broker or exchange order placement without a separate explicit project decision.
- Never hard-code API keys or credentials.
- Demo registry metrics are synthetic and must remain labeled as such.
- Update tests and documentation with behavior changes.
- Prefer narrow `Choice`, `Score`, and `Noul` questions over one broad judgment.
