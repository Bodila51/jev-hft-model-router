from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from jev_hft_router.api import create_app
from jev_hft_router.backends import HeuristicDecisionBackend
from jev_hft_router.registry import StrategyRegistry
from jev_hft_router.router import HftModelRouter
from jev_hft_router.settings import Policy


ROOT = Path(__file__).resolve().parents[1]


def test_http_api_routes_request() -> None:
    router = HftModelRouter(
        registry=StrategyRegistry.from_path(ROOT / "config" / "model_registry.demo.json"),
        backend=HeuristicDecisionBackend(),
        policy=Policy(min_selection_confidence=0.40),
    )
    client = TestClient(create_app(router))
    response = client.post(
        "/v1/route",
        json={
            "query": "Choose a VWAP execution model for a large futures parent order.",
            "constraints": {"asset_class": "futures", "capital_usd": 500000},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["classification"]["family"] == "execution"
    assert payload["execution_allowed"] is False


def test_health_reports_registry_size() -> None:
    router = HftModelRouter(
        registry=StrategyRegistry.from_path(ROOT / "config" / "model_registry.demo.json"),
        backend=HeuristicDecisionBackend(),
        policy=Policy(),
    )
    client = TestClient(create_app(router))
    payload = client.get("/health").json()
    assert payload["registered_models"] == 200
    assert payload["trade_execution"] is False
