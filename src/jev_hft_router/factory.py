from __future__ import annotations

from .audit import AuditLogger
from .backends import build_backend
from .registry import StrategyRegistry
from .router import HftModelRouter
from .settings import load_policy, load_settings


def build_router() -> HftModelRouter:
    settings = load_settings()
    registry = StrategyRegistry.from_path(settings.registry_path)
    policy = load_policy(settings.policy_path)
    backend = build_backend(settings.backend, settings.model)
    return HftModelRouter(
        registry=registry,
        backend=backend,
        policy=policy,
        audit_logger=AuditLogger(settings.audit_log_path),
    )
