from __future__ import annotations

import json
from pathlib import Path

from .domain import Classification, RouteRequest, StrategyProfile


class StrategyRegistry:
    def __init__(self, models: list[StrategyProfile]) -> None:
        ids = [model.id for model in models]
        if len(ids) != len(set(ids)):
            raise ValueError("Strategy registry contains duplicate model ids")
        if not models:
            raise ValueError("Strategy registry is empty")
        self.models = models
        self._by_id = {model.id: model for model in models}

    @classmethod
    def from_path(cls, path: Path) -> "StrategyRegistry":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("models", [])
        return cls([StrategyProfile.model_validate(item) for item in payload])

    def get(self, model_id: str) -> StrategyProfile:
        return self._by_id[model_id]

    def __contains__(self, model_id: str) -> bool:
        return model_id in self._by_id

    def eligible(
        self,
        request: RouteRequest,
        classification: Classification,
    ) -> list[StrategyProfile]:
        constraints = request.constraints
        market = request.market
        asset_class = constraints.asset_class or (market.asset_class if market else None)
        symbol = constraints.symbol or (market.symbol if market else None)
        venue = constraints.venue or (market.venue if market else None)

        eligible: list[StrategyProfile] = []
        for model in self.models:
            if not model.enabled or model.id in constraints.excluded_models:
                continue
            if constraints.require_production_ready and not model.production_ready:
                continue
            if constraints.allowed_families and model.family not in constraints.allowed_families:
                continue
            if asset_class and asset_class.lower() not in {
                value.lower() for value in model.asset_classes
            }:
                continue
            if symbol and "*" not in model.symbols and symbol.upper() not in {
                value.upper() for value in model.symbols
            }:
                continue
            if venue and "generic" not in model.venues and venue.lower() not in {
                value.lower() for value in model.venues
            }:
                continue
            if (
                constraints.capital_usd is not None
                and constraints.capital_usd < model.min_capital_usd
            ):
                continue
            if (
                constraints.available_latency_ms is not None
                and model.max_acceptable_latency_ms is not None
                and constraints.available_latency_ms > model.max_acceptable_latency_ms
            ):
                continue
            if (
                constraints.max_drawdown is not None
                and model.metrics.max_drawdown is not None
                and model.metrics.max_drawdown > constraints.max_drawdown
            ):
                continue
            if (
                constraints.max_risk_level is not None
                and model.risk_level > constraints.max_risk_level
            ):
                continue
            eligible.append(model)

        return eligible


def registry_summary(models: list[StrategyProfile]) -> dict[str, dict]:
    return {model.id: model.compact_choice_description() for model in models}
