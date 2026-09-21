from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .domain import MarketSnapshot, RouteRequest, UserConstraints
from .factory import build_router
from .registry import StrategyRegistry


def _load_json(value: str | None) -> dict:
    if not value:
        return {}
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def _print_response(response) -> None:
    print(json.dumps(response.model_dump(mode="json"), indent=2))


def command_route(args: argparse.Namespace) -> int:
    market_payload = _load_json(args.market)
    constraints_payload = _load_json(args.constraints)
    request = RouteRequest(
        query=args.query,
        market=MarketSnapshot.model_validate(market_payload) if market_payload else None,
        constraints=UserConstraints.model_validate(constraints_payload),
    )
    _print_response(build_router().route(request))
    return 0


def command_chat(_: argparse.Namespace) -> int:
    router = build_router()
    market: MarketSnapshot | None = None
    constraints = UserConstraints()
    print("Jev HFT Router chat")
    print("Commands: /market {json}, /constraints {json}, /clear, /exit")
    print("This tool recommends registered models; it never executes trades.\n")
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in {"/exit", "/quit"}:
            return 0
        if line == "/clear":
            market = None
            constraints = UserConstraints()
            print("context cleared")
            continue
        if line.startswith("/market "):
            market = MarketSnapshot.model_validate(json.loads(line[8:]))
            print("market context updated")
            continue
        if line.startswith("/constraints "):
            constraints = UserConstraints.model_validate(json.loads(line[13:]))
            print("constraints updated")
            continue
        response = router.route(
            RouteRequest(query=line, market=market, constraints=constraints)
        )
        if response.selected_model:
            print(
                f"jev> {response.status}: {response.selected_model.id} — "
                f"{response.selected_model.name} "
                f"(confidence {response.confidence:.2f})"
            )
        else:
            print(
                f"jev> {response.status} "
                f"(confidence {response.confidence:.2f}; "
                f"reasons: {', '.join(response.reason_codes)})"
            )


def command_validate(args: argparse.Namespace) -> int:
    registry = StrategyRegistry.from_path(Path(args.registry))
    print(f"valid registry: {len(registry.models)} unique models")
    demo = sum(model.source == "synthetic-demo" for model in registry.models)
    production = sum(model.production_ready for model in registry.models)
    print(f"synthetic demo profiles: {demo}")
    print(f"production-ready profiles: {production}")
    return 0


def command_evaluate(args: argparse.Namespace) -> int:
    router = build_router()
    scenarios = json.loads(Path(args.scenarios).read_text(encoding="utf-8"))
    correct_family = 0
    correct_status = 0
    for scenario in scenarios:
        request = RouteRequest.model_validate(scenario["request"])
        response = router.route(request)
        family_ok = response.classification.family == scenario["expected_family"]
        status_ok = response.status in scenario["acceptable_statuses"]
        correct_family += int(family_ok)
        correct_status += int(status_ok)
        print(
            f"{scenario['id']}: family={'PASS' if family_ok else 'FAIL'} "
            f"status={'PASS' if status_ok else 'FAIL'}"
        )
    count = max(1, len(scenarios))
    print(f"family accuracy: {correct_family / count:.1%}")
    print(f"status accuracy: {correct_status / count:.1%}")
    return 0 if correct_family == len(scenarios) else 1


def command_serve(_: argparse.Namespace) -> int:
    try:
        from .api import run as run_api
    except ImportError as exc:
        raise RuntimeError(
            "HTTP dependencies are missing. Install the project with: pip install -e ."
        ) from exc
    run_api()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jev-hft",
        description="Route trading requests to a best-fit registered HFT model.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    route = sub.add_parser("route", help="Route one request")
    route.add_argument("query")
    route.add_argument("--market", help="JSON object or path to a JSON file")
    route.add_argument("--constraints", help="JSON object or path to a JSON file")
    route.set_defaults(func=command_route)

    chat = sub.add_parser("chat", help="Start a local interactive chat")
    chat.set_defaults(func=command_chat)

    serve = sub.add_parser("serve", help="Start the HTTP API and browser chat")
    serve.set_defaults(func=command_serve)

    validate = sub.add_parser("validate-registry", help="Validate model cards")
    validate.add_argument(
        "--registry", default=os.getenv("JEV_HFT_REGISTRY", "config/model_registry.demo.json")
    )
    validate.set_defaults(func=command_validate)

    evaluate = sub.add_parser("evaluate", help="Run labeled routing scenarios")
    evaluate.add_argument(
        "--scenarios", default="config/evaluation_scenarios.json"
    )
    evaluate.set_defaults(func=command_evaluate)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        code = args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    main()
