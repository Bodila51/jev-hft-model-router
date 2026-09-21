from __future__ import annotations

import json

from .domain import MarketSnapshot, RouteRequest, UserConstraints
from .factory import build_router


def run() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit(
            "MCP support is optional. Install it with: pip install -e '.[mcp]'"
        ) from exc

    router = build_router()
    mcp = FastMCP("Jev HFT Model Router")

    @mcp.tool()
    def recommend_hft_model(
        query: str,
        market_json: str = "{}",
        constraints_json: str = "{}",
    ) -> str:
        """Select a best-fit registered HFT model without executing a trade."""
        market_payload = json.loads(market_json)
        constraints_payload = json.loads(constraints_json)
        request = RouteRequest(
            query=query,
            market=(
                MarketSnapshot.model_validate(market_payload)
                if market_payload
                else None
            ),
            constraints=UserConstraints.model_validate(constraints_payload),
        )
        response = router.route(request)
        return response.model_dump_json(indent=2)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
