from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .audit import AuditLogger
from .backends import DecisionBackend
from .domain import Alternative, Classification, RouteRequest, RouteResponse
from .registry import StrategyRegistry
from .settings import Policy


class HftModelRouter:
    def __init__(
        self,
        registry: StrategyRegistry,
        backend: DecisionBackend,
        policy: Policy,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.registry = registry
        self.backend = backend
        self.policy = policy
        self.audit_logger = audit_logger

    def route(self, request: RouteRequest) -> RouteResponse:
        request_id = request.request_id or str(uuid4())
        classification = self.backend.classify(request)

        if classification.abstain_probability > self.policy.max_abstain_probability:
            return self._finish(
                request,
                RouteResponse(
                    request_id=request_id,
                    status="no_trade",
                    confidence=classification.confidence,
                    classification=classification,
                    reason_codes=["INSUFFICIENT_REQUEST_DETAIL"],
                    scanned_models=len(self.registry.models),
                    eligible_models=0,
                    backend=self.backend.name,
                ),
            )

        if (
            classification.requires_live_data_probability
            >= self.policy.live_data_requirement_threshold
            and not self._market_is_fresh(request)
        ):
            return self._finish(
                request,
                RouteResponse(
                    request_id=request_id,
                    status="no_trade",
                    confidence=classification.confidence,
                    classification=classification,
                    reason_codes=["FRESH_MARKET_DATA_REQUIRED"],
                    scanned_models=len(self.registry.models),
                    eligible_models=0,
                    backend=self.backend.name,
                ),
            )

        candidates = self.registry.eligible(request, classification)
        if not candidates:
            return self._finish(
                request,
                RouteResponse(
                    request_id=request_id,
                    status="no_trade",
                    confidence=1.0,
                    classification=classification,
                    reason_codes=["NO_COMPATIBLE_REGISTERED_MODEL"],
                    scanned_models=len(self.registry.models),
                    eligible_models=0,
                    backend=self.backend.name,
                ),
            )

        eligible_count = len(candidates)
        if len(candidates) > self.policy.max_choice_options:
            candidates = self._deterministic_preselect(candidates, classification)

        selection = self.backend.select(
            request=request,
            classification=classification,
            candidates=candidates,
            include_no_trade=self.policy.include_no_trade_option,
        )

        alternatives = self._alternatives(
            selection.probabilities,
            excluded_id=(selection.choice if selection.choice != "no_trade" else None),
        )
        if selection.choice == "no_trade":
            response = RouteResponse(
                request_id=request_id,
                status="no_trade",
                confidence=selection.confidence,
                classification=classification,
                alternatives=alternatives,
                reason_codes=["JEV_SELECTED_NO_TRADE"],
                scanned_models=len(self.registry.models),
                eligible_models=eligible_count,
                backend=self.backend.name,
            )
        elif selection.confidence < self.policy.min_selection_confidence:
            response = RouteResponse(
                request_id=request_id,
                status="review_required",
                confidence=selection.confidence,
                classification=classification,
                alternatives=alternatives,
                reason_codes=["LOW_SELECTION_CONFIDENCE"],
                scanned_models=len(self.registry.models),
                eligible_models=eligible_count,
                backend=self.backend.name,
            )
        else:
            selected = self.registry.get(selection.choice)
            reason_codes = [
                "BEST_FIT_IN_CONNECTED_REGISTRY",
                f"FAMILY_{selected.family.upper()}",
            ]
            if not selected.production_ready:
                reason_codes.append("MODEL_NOT_MARKED_PRODUCTION_READY")
            response = RouteResponse(
                request_id=request_id,
                status="selected",
                selected_model=selected,
                confidence=selection.confidence,
                classification=classification,
                alternatives=alternatives,
                reason_codes=reason_codes,
                scanned_models=len(self.registry.models),
                eligible_models=eligible_count,
                backend=self.backend.name,
            )
        return self._finish(request, response)

    def _market_is_fresh(self, request: RouteRequest) -> bool:
        if request.market is None:
            return False
        now = datetime.now(timezone.utc)
        age = (now - request.market.timestamp.astimezone(timezone.utc)).total_seconds()
        return 0 <= age <= self.policy.max_market_data_age_seconds

    def _deterministic_preselect(
        self,
        candidates,
        classification: Classification,
    ):
        def key(model):
            family = int(model.family == classification.family)
            regime = int(classification.regime in model.regimes)
            horizon = int(classification.horizon in model.horizons)
            evidence = model.metrics.oos_sharpe or -99.0
            return (family, regime, horizon, evidence)

        return sorted(candidates, key=key, reverse=True)[
            : self.policy.max_choice_options
        ]

    def _alternatives(
        self,
        probabilities: dict[str, float],
        excluded_id: str | None = None,
    ) -> list[Alternative]:
        alternatives: list[Alternative] = []
        for model_id, probability in sorted(
            probabilities.items(), key=lambda item: item[1], reverse=True
        ):
            if (
                model_id == "no_trade"
                or model_id == excluded_id
                or model_id not in self.registry
            ):
                continue
            model = self.registry.get(model_id)
            alternatives.append(
                Alternative(
                    model_id=model.id,
                    name=model.name,
                    probability=probability,
                )
            )
            if len(alternatives) >= self.policy.alternative_count:
                break
        return alternatives

    def _finish(self, request: RouteRequest, response: RouteResponse) -> RouteResponse:
        if self.audit_logger:
            self.audit_logger.write(request, response)
        return response
