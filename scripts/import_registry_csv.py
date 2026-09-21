#!/usr/bin/env python3
"""Convert a user-maintained CSV into registry JSON, then validate it."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


LIST_FIELDS = {
    "asset_classes",
    "symbols",
    "venues",
    "horizons",
    "regimes",
    "strengths",
    "weaknesses",
}

METRIC_FIELDS = {
    "net_return",
    "sharpe",
    "oos_sharpe",
    "max_drawdown",
    "win_rate",
    "latency_ms",
    "slippage_bps",
    "capacity_usd",
    "walk_forward_passes",
    "regime_consistency",
    "sample_start",
    "sample_end",
}


def convert(value: str):
    value = value.strip()
    if value == "":
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("output_json")
    args = parser.parse_args()
    rows: list[dict] = []
    with Path(args.input_csv).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            model: dict = {"metrics": {}}
            for key, raw in row.items():
                if raw is None or raw.strip() == "":
                    continue
                if key in LIST_FIELDS:
                    model[key] = [part.strip() for part in raw.split("|") if part.strip()]
                elif key in METRIC_FIELDS:
                    model["metrics"][key] = convert(raw)
                else:
                    model[key] = convert(raw)
            rows.append(model)
    Path(args.output_json).write_text(json.dumps({"models": rows}, indent=2) + "\n")
    print(f"wrote {len(rows)} model cards to {args.output_json}")


if __name__ == "__main__":
    main()
