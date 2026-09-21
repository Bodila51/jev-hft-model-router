from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .domain import RouteRequest, RouteResponse, StrategyProfile
from .factory import build_router
from .router import HftModelRouter


@lru_cache(maxsize=1)
def get_router() -> HftModelRouter:
    return build_router()


def create_app(router: HftModelRouter | None = None) -> FastAPI:
    app = FastAPI(
        title="Jev HFT Model Router",
        version="0.1.0",
        description=(
            "Selects a best-fit strategy from a connected registry. "
            "Research and paper-testing only; no trade execution."
        ),
    )
    injected_router = router

    def active_router() -> HftModelRouter:
        return injected_router or get_router()

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        path = Path(__file__).parent / "web" / "index.html"
        return HTMLResponse(path.read_text(encoding="utf-8"))

    @app.get("/health")
    def health() -> dict:
        instance = active_router()
        return {
            "status": "ok",
            "backend": instance.backend.name,
            "registered_models": len(instance.registry.models),
            "trade_execution": False,
        }

    @app.get("/v1/models", response_model=list[StrategyProfile])
    def models() -> list[StrategyProfile]:
        return active_router().registry.models

    @app.post("/v1/route", response_model=RouteResponse)
    def route(request: RouteRequest) -> RouteResponse:
        return active_router().route(request)

    return app


app = create_app()


def run() -> None:
    uvicorn.run(
        "jev_hft_router.api:app",
        host=os.getenv("JEV_HFT_HOST", "127.0.0.1"),
        port=int(os.getenv("JEV_HFT_PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    run()
