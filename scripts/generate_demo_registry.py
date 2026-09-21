#!/usr/bin/env python3
"""Generate 200 deterministic synthetic model cards for UI and routing demos."""

from __future__ import annotations

import json
from pathlib import Path


FAMILIES = {
    "market_making": {
        "label": "Adaptive Market Maker",
        "regimes": ["range_bound", "low_volatility", "mixed"],
        "horizons": ["milliseconds", "seconds"],
        "strengths": ["spread capture", "inventory-aware quoting", "high turnover"],
        "weaknesses": ["adverse selection", "latency sensitivity", "inventory risk"],
    },
    "statistical_arbitrage": {
        "label": "Statistical Arbitrage",
        "regimes": ["range_bound", "mixed"],
        "horizons": ["seconds", "minutes"],
        "strengths": ["relative-value signals", "market neutrality", "portfolio breadth"],
        "weaknesses": ["correlation breaks", "crowding", "model decay"],
    },
    "cross_venue_arbitrage": {
        "label": "Cross-Venue Arbitrage",
        "regimes": ["high_volatility", "mixed"],
        "horizons": ["milliseconds", "seconds"],
        "strengths": ["price dislocation capture", "venue diversification", "short holding period"],
        "weaknesses": ["transfer constraints", "fee sensitivity", "execution race"],
    },
    "mean_reversion": {
        "label": "Micro Mean Reversion",
        "regimes": ["range_bound", "low_volatility"],
        "horizons": ["seconds", "minutes"],
        "strengths": ["temporary dislocation capture", "clear exits", "range efficiency"],
        "weaknesses": ["trend exposure", "gap risk", "parameter decay"],
    },
    "trend_following": {
        "label": "Intraday Momentum",
        "regimes": ["trending_up", "trending_down", "high_volatility"],
        "horizons": ["seconds", "minutes"],
        "strengths": ["directional persistence", "breakout capture", "convex payoff"],
        "weaknesses": ["whipsaw", "late entries", "reversal risk"],
    },
    "volatility": {
        "label": "Volatility Response",
        "regimes": ["high_volatility", "event_driven", "mixed"],
        "horizons": ["milliseconds", "seconds", "minutes"],
        "strengths": ["volatility adaptation", "event response", "dynamic sizing"],
        "weaknesses": ["tail exposure", "calibration risk", "spread expansion"],
    },
    "execution": {
        "label": "Adaptive Execution",
        "regimes": ["mixed", "high_volatility", "low_volatility"],
        "horizons": ["seconds", "minutes", "hours"],
        "strengths": ["impact control", "schedule adaptation", "liquidity seeking"],
        "weaknesses": ["benchmark risk", "information leakage", "partial fills"],
    },
    "event_driven": {
        "label": "Event Reaction",
        "regimes": ["event_driven", "high_volatility"],
        "horizons": ["milliseconds", "seconds"],
        "strengths": ["fast event response", "state-aware routing", "asymmetric opportunity"],
        "weaknesses": ["false positives", "news latency", "gap risk"],
    },
}

ASSET_CONFIG = [
    ("crypto", ["BTC-USDT", "ETH-USDT", "*"], ["binance", "coinbase"]),
    ("equities", ["AAPL", "MSFT", "NVDA", "*"], ["nasdaq", "nyse"]),
    ("futures", ["ES", "NQ", "CL", "*"], ["cme"]),
    ("fx", ["EUR-USD", "USD-JPY", "GBP-USD", "*"], ["ecns", "generic"]),
]


def build_registry() -> list[dict]:
    registry: list[dict] = []
    for family_index, (family, config) in enumerate(FAMILIES.items()):
        for variant in range(1, 26):
            asset, symbols, venues = ASSET_CONFIG[(variant - 1) % len(ASSET_CONFIG)]
            risk = 1 + ((variant + family_index) % 5)
            max_latency = [0.5, 1.0, 2.0, 5.0, 10.0][(variant + family_index) % 5]
            oos_sharpe = round(0.65 + ((variant * 7 + family_index * 3) % 160) / 100, 2)
            max_drawdown = round(0.025 + ((variant * 11 + family_index * 5) % 120) / 1000, 3)
            registry.append(
                {
                    "id": f"demo-{family.replace('_', '-')}-{variant:03d}",
                    "name": f"{config['label']} {variant:02d}",
                    "description": (
                        f"Synthetic {asset} demo profile for the {family.replace('_', ' ')} "
                        "family. Replace this card with evidence from your own strategy."
                    ),
                    "family": family,
                    "asset_classes": [asset],
                    "symbols": symbols,
                    "venues": venues,
                    "horizons": config["horizons"],
                    "regimes": config["regimes"],
                    "min_capital_usd": 5_000 * (1 + variant % 10),
                    "max_acceptable_latency_ms": max_latency,
                    "risk_level": risk,
                    "requires_live_order_book": family
                    in {"market_making", "cross_venue_arbitrage", "execution"},
                    "strengths": config["strengths"],
                    "weaknesses": config["weaknesses"],
                    "metrics": {
                        "net_return": round(0.03 + ((variant * 13) % 180) / 1000, 3),
                        "sharpe": round(oos_sharpe + 0.25, 2),
                        "oos_sharpe": oos_sharpe,
                        "max_drawdown": max_drawdown,
                        "win_rate": round(0.48 + ((variant * 3) % 14) / 100, 2),
                        "latency_ms": max_latency * 0.7,
                        "slippage_bps": round(0.2 + ((variant * 5) % 20) / 10, 2),
                        "capacity_usd": 250_000 * (1 + variant % 8),
                        "walk_forward_passes": 4 + variant % 9,
                        "regime_consistency": round(0.50 + ((variant * 7) % 45) / 100, 2),
                        "sample_start": "2024-01-01",
                        "sample_end": "2026-06-30",
                    },
                    "source": "synthetic-demo",
                    "production_ready": False,
                    "enabled": True,
                }
            )
    assert len(registry) == 200
    return registry


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    target = root / "config" / "model_registry.demo.json"
    target.write_text(json.dumps({"models": build_registry()}, indent=2) + "\n")
    print(f"wrote 200 synthetic demo profiles to {target}")
