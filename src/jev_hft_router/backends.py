from __future__ import annotations

import math
import os
import re
from abc import ABC, abstractmethod
from typing import Any

from .domain import (
    Classification,
    Horizon,
    MarketRegime,
    RouteRequest,
    Selection,
    StrategyFamily,
    StrategyProfile,
)
from .registry import registry_summary


FAMILY_CRITERIA: dict[str, str] = {
    "market_making": "Continuously quotes both sides and earns spread/rebates.",
    "statistical_arbitrage": "Trades relative-value signals across related instruments.",
    "cross_venue_arbitrage": "Captures price differences across venues.",
    "mean_reversion": "Trades temporary deviations back toward an estimated mean.",
    "trend_following": "Trades persistent directional movement.",
    "volatility": "Trades volatility, dispersion, or rapid changes in realized risk.",
    "execution": "Minimizes market impact while executing an existing parent order.",
    "event_driven": "Responds to scheduled or detected market events.",
}

HORIZON_CRITERIA: dict[str, str] = {
    "microseconds": "Sub-millisecond reaction and colocated infrastructure.",
    "milliseconds": "Single- to double-digit millisecond decisions.",
    "seconds": "Positions typically live for seconds.",
    "minutes": "Positions typically live for minutes.",
    "hours": "Intraday positions that can live for hours.",
}

REGIME_CRITERIA: dict[str, str] = {
    "trending_up": "Persistent positive directional movement.",
    "trending_down": "Persistent negative directional movement.",
    "range_bound": "Price oscillates without a durable direction.",
    "high_volatility": "Large and rapid price changes dominate.",
    "low_volatility": "Small price changes and stable conditions dominate.",
    "event_driven": "A scheduled or detected event dominates behavior.",
    "mixed": "Several regimes are present or the request requires robustness.",
    "unknown": "The supplied state does not identify a regime.",
}


class DecisionBackend(ABC):
    name: str

    @abstractmethod
    def classify(self, request: RouteRequest) -> Classification:
        raise NotImplementedError

    @abstractmethod
    def select(
        self,
        request: RouteRequest,
        classification: Classification,
        candidates: list[StrategyProfile],
        include_no_trade: bool,
    ) -> Selection:
        raise NotImplementedError


class JevDecisionBackend(DecisionBackend):
    name = "jev"

    def __init__(self, model: str = "jev-latest") -> None:
        if not os.getenv("TYPESAFE_API_KEY"):
            raise RuntimeError("TYPESAFE_API_KEY is required for the Jev backend")
        try:
            from typesafe_sdk import TypeSafeClient
        except ImportError as exc:
            raise RuntimeError(
                "typesafe-sdk is not installed. Run: pip install typesafe-sdk"
            ) from exc
        self._typesafe = __import__("typesafe_sdk", fromlist=["Choice", "Noul", "Score"])
        self._client = TypeSafeClient()
        self._model = model

    def classify(self, request: RouteRequest) -> Classification:
        Choice = self._typesafe.Choice
        Noul = self._typesafe.Noul
        Score = self._typesafe.Score

        response = self._client.system_one(
            state={
                "user_request": request.query,
                "market_snapshot": (
                    request.market.model_dump(mode="json") if request.market else None
                ),
                "constraints": request.constraints.model_dump(mode="json"),
            },
            questions={
                "family": Choice(
                    instructions="Which strategy family best matches the user's goal?",
                    criteria=FAMILY_CRITERIA,
                ),
                "horizon": Choice(
                    instructions="Which holding or reaction horizon best matches the request?",
                    criteria=HORIZON_CRITERIA,
                ),
                "regime": Choice(
                    instructions="Which market regime is most relevant to this request?",
                    criteria=REGIME_CRITERIA,
                ),
                "risk": Score(
                    instructions="How much strategy and execution risk does this request tolerate?",
                    criteria=[
                        "Minimal risk tolerance",
                        "Low risk tolerance",
                        "Moderate risk tolerance",
                        "High risk tolerance",
                        "Very high risk tolerance",
                    ],
                ),
                "abstain": Noul(
                    instructions=(
                        "The supplied request and state are too ambiguous or incomplete "
                        "to choose an HFT strategy safely."
                    )
                ),
                "requires_live_data": Noul(
                    instructions=(
                        "A responsible answer to this request depends on fresh live market data."
                    )
                ),
            },
            model=self._model,
        )
        answers = response.answers
        choice_confidences = [
            float(answers["family"].confidence),
            float(answers["horizon"].confidence),
            float(answers["regime"].confidence),
        ]
        return Classification(
            family=answers["family"].choice,
            horizon=answers["horizon"].choice,
            regime=answers["regime"].choice,
            risk_score=float(answers["risk"].score),
            abstain_probability=float(answers["abstain"].noul),
            requires_live_data_probability=float(answers["requires_live_data"].noul),
            confidence=sum(choice_confidences) / len(choice_confidences),
        )

    def select(
        self,
        request: RouteRequest,
        classification: Classification,
        candidates: list[StrategyProfile],
        include_no_trade: bool,
    ) -> Selection:
        Choice = self._typesafe.Choice
        criteria: dict[str, Any] = registry_summary(candidates)
        if include_no_trade:
            criteria["no_trade"] = {
                "description": (
                    "Choose this when no candidate has enough evidence, compatibility, "
                    "or safety for the supplied situation."
                )
            }
        response = self._client.system_one(
            state={
                "user_request": request.query,
                "market_snapshot": (
                    request.market.model_dump(mode="json") if request.market else None
                ),
                "constraints": request.constraints.model_dump(mode="json"),
                "classified_intent": classification.model_dump(mode="json"),
                "selection_policy": (
                    "Select the best-fit registered strategy, not the strategy with the "
                    "largest backtest return. Prefer out-of-sample robustness, operational "
                    "compatibility, controlled drawdown, and evidence quality. Abstain when "
                    "evidence is insufficient."
                ),
            },
            questions={
                "strategy": Choice(
                    instructions=(
                        "Which registered strategy is the strongest defensible fit for this "
                        "request and current state?"
                    ),
                    criteria=criteria,
                )
            },
            model=self._model,
        )
        answer = response.answers["strategy"]
        return Selection(
            choice=answer.choice,
            confidence=float(answer.confidence),
            probabilities={key: float(value) for key, value in answer.probabilities.items()},
        )


class HeuristicDecisionBackend(DecisionBackend):
    """Deterministic offline demo. It is deliberately not presented as Jev."""

    name = "heuristic-demo"

    _family_words: dict[StrategyFamily, tuple[str, ...]] = {
        "market_making": ("market make", "market-making", "spread", "quote both"),
        "statistical_arbitrage": ("stat arb", "pairs", "relative value", "cointegration"),
        "cross_venue_arbitrage": ("arbitrage", "cross-venue", "cross exchange"),
        "mean_reversion": ("mean revert", "reversion", "range", "oversold"),
        "trend_following": ("trend", "momentum", "breakout", "directional"),
        "volatility": ("volatility", "vol", "dispersion", "gamma"),
        "execution": ("execute", "vwap", "twap", "market impact", "parent order"),
        "event_driven": ("event", "news", "earnings", "announcement"),
    }

    def classify(self, request: RouteRequest) -> Classification:
        text = request.query.lower()
        family: StrategyFamily = "statistical_arbitrage"
        best_hits = 0
        for candidate, words in self._family_words.items():
            hits = sum(word in text for word in words)
            if hits > best_hits:
                family = candidate
                best_hits = hits

        if any(word in text for word in ("microsecond", "colocation", "fpga")):
            horizon: Horizon = "microseconds"
        elif any(word in text for word in ("millisecond", "latency", "hft")):
            horizon = "milliseconds"
        elif "minute" in text:
            horizon = "minutes"
        elif "hour" in text or "intraday" in text:
            horizon = "hours"
        else:
            horizon = "seconds"

        regime: MarketRegime = request.market.regime if request.market else "unknown"
        if regime == "unknown":
            if any(word in text for word in ("high vol", "volatile", "crash")):
                regime = "high_volatility"
            elif any(word in text for word in ("low vol", "quiet")):
                regime = "low_volatility"
            elif any(word in text for word in ("range", "sideways")):
                regime = "range_bound"
            elif any(word in text for word in ("uptrend", "bull")):
                regime = "trending_up"
            elif any(word in text for word in ("downtrend", "bear")):
                regime = "trending_down"

        live_words = ("now", "today", "current", "live", "right now")
        requires_live = 0.92 if any(word in text for word in live_words) else 0.18
        ambiguity = 0.72 if len(re.findall(r"\w+", text)) < 5 else 0.18
        confidence = 0.72 if best_hits else 0.46

        return Classification(
            family=family,
            horizon=horizon,
            regime=regime,
            risk_score=2.0,
            abstain_probability=ambiguity,
            requires_live_data_probability=requires_live,
            confidence=confidence,
        )

    def select(
        self,
        request: RouteRequest,
        classification: Classification,
        candidates: list[StrategyProfile],
        include_no_trade: bool,
    ) -> Selection:
        raw: dict[str, float] = {}
        for model in candidates:
            score = 0.0
            score += 2.5 if model.family == classification.family else 0.0
            score += 1.5 if classification.regime in model.regimes else 0.0
            score += 1.0 if classification.horizon in model.horizons else 0.0
            score += max(0.0, 1.0 - abs(model.risk_level - classification.risk_score) / 4)
            if model.metrics.oos_sharpe is not None:
                score += min(max(model.metrics.oos_sharpe, -1.0), 3.0) / 3.0
            if model.metrics.max_drawdown is not None:
                score += max(0.0, 1.0 - model.metrics.max_drawdown)
            if model.production_ready:
                score += 0.35
            raw[model.id] = score

        if include_no_trade:
            raw["no_trade"] = 4.5 * classification.abstain_probability

        if not raw:
            return Selection(choice="no_trade", confidence=1.0, probabilities={"no_trade": 1.0})

        max_score = max(raw.values())
        exps = {key: math.exp((value - max_score) * 1.4) for key, value in raw.items()}
        total = sum(exps.values())
        probabilities = {key: value / total for key, value in exps.items()}
        ordered = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
        choice, top = ordered[0]
        second = ordered[1][1] if len(ordered) > 1 else 0.0
        confidence = min(1.0, max(0.0, 0.45 + (top - second) * 3.0))
        return Selection(choice=choice, confidence=confidence, probabilities=probabilities)


def build_backend(name: str, model: str) -> DecisionBackend:
    normalized = name.lower()
    if normalized == "jev":
        return JevDecisionBackend(model=model)
    if normalized == "heuristic":
        return HeuristicDecisionBackend()
    if normalized == "auto":
        if os.getenv("TYPESAFE_API_KEY"):
            return JevDecisionBackend(model=model)
        return HeuristicDecisionBackend()
    raise ValueError("JEV_HFT_BACKEND must be one of: auto, jev, heuristic")
