from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
except ImportError:  # Core routing tests can run before optional app deps are installed.
    def load_dotenv() -> bool:
        return False


class Policy(BaseModel):
    min_selection_confidence: float = Field(default=0.45, ge=0, le=1)
    max_abstain_probability: float = Field(default=0.65, ge=0, le=1)
    live_data_requirement_threshold: float = Field(default=0.55, ge=0, le=1)
    max_market_data_age_seconds: int = Field(default=30, ge=1)
    max_choice_options: int = Field(default=254, ge=2, le=254)
    alternative_count: int = Field(default=3, ge=0, le=10)
    include_no_trade_option: bool = True


class Settings(BaseModel):
    backend: str = "auto"
    registry_path: Path = Path("config/model_registry.demo.json")
    policy_path: Path = Path("config/policy.json")
    audit_log_path: Path = Path("data/audit.jsonl")
    model: str = "jev-latest"


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        backend=os.getenv("JEV_HFT_BACKEND", "auto").lower(),
        registry_path=Path(
            os.getenv("JEV_HFT_REGISTRY", "config/model_registry.demo.json")
        ),
        policy_path=Path(os.getenv("JEV_HFT_POLICY", "config/policy.json")),
        audit_log_path=Path(
            os.getenv("JEV_HFT_AUDIT_LOG", "data/audit.jsonl")
        ),
        model=os.getenv("JEV_HFT_MODEL", "jev-latest"),
    )


def load_policy(path: Path) -> Policy:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return Policy.model_validate(payload)
