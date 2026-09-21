from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jev_hft_router.audit import AuditLogger
from jev_hft_router.backends import HeuristicDecisionBackend
from jev_hft_router.domain import MarketSnapshot, RouteRequest, UserConstraints
from jev_hft_router.registry import StrategyRegistry
from jev_hft_router.router import HftModelRouter
from jev_hft_router.settings import Policy


ROOT = Path(__file__).resolve().parents[1]


def build_test_router(tmp_path: Path | None = None) -> HftModelRouter:
    registry = StrategyRegistry.from_path(ROOT / "config" / "model_registry.demo.json")
    audit = AuditLogger(tmp_path / "audit.jsonl") if tmp_path else None
    return HftModelRouter(
        registry=registry,
        backend=HeuristicDecisionBackend(),
        policy=Policy(min_selection_confidence=0.40),
        audit_logger=audit,
    )


def test_demo_registry_has_exactly_200_unique_models() -> None:
    registry = StrategyRegistry.from_path(ROOT / "config" / "model_registry.demo.json")
    assert len(registry.models) == 200
    assert len({model.id for model in registry.models}) == 200
    assert all(model.source == "synthetic-demo" for model in registry.models)
    assert not any(model.production_ready for model in registry.models)


def test_routes_market_making_request() -> None:
    router = build_test_router()
    response = router.route(
        RouteRequest(
            query="Find a low-risk market-making model for BTC in a range-bound market.",
            constraints=UserConstraints(
                asset_class="crypto",
                symbol="BTC-USDT",
                venue="binance",
                capital_usd=100_000,
                available_latency_ms=1,
                max_risk_level=3,
            ),
        )
    )
    assert response.status == "selected"
    assert response.selected_model is not None
    assert response.selected_model.family == "market_making"
    assert response.scanned_models == 200
    assert response.execution_allowed is False


def test_live_request_without_snapshot_abstains() -> None:
    router = build_test_router()
    response = router.route(
        RouteRequest(query="Which volatility model should I run on BTC right now?")
    )
    assert response.status == "no_trade"
    assert "FRESH_MARKET_DATA_REQUIRED" in response.reason_codes


def test_live_request_accepts_fresh_snapshot() -> None:
    router = build_test_router()
    response = router.route(
        RouteRequest(
            query="Which volatility model fits BTC right now?",
            market=MarketSnapshot(
                timestamp=datetime.now(timezone.utc),
                asset_class="crypto",
                symbol="BTC-USDT",
                regime="high_volatility",
            ),
        )
    )
    assert response.status in {"selected", "review_required"}
    if response.selected_model:
        assert response.selected_model.family == "volatility"


def test_impossible_capital_constraint_returns_no_trade() -> None:
    router = build_test_router()
    response = router.route(
        RouteRequest(
            query="Find a statistical arbitrage model for an equities pairs trade.",
            constraints=UserConstraints(asset_class="equities", capital_usd=1),
        )
    )
    assert response.status == "no_trade"
    assert "NO_COMPATIBLE_REGISTERED_MODEL" in response.reason_codes


def test_audit_log_hashes_query_instead_of_storing_it(tmp_path: Path) -> None:
    router = build_test_router(tmp_path)
    secret_prompt = "Find a mean reversion model for a private research scenario."
    router.route(RouteRequest(query=secret_prompt))
    line = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    event = json.loads(line)
    assert secret_prompt not in line
    assert len(event["query_sha256"]) == 64
