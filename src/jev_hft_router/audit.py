from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .domain import RouteRequest, RouteResponse


class AuditLogger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write(self, request: RouteRequest, response: RouteResponse) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        query_hash = hashlib.sha256(request.query.encode("utf-8")).hexdigest()
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": response.request_id,
            "query_sha256": query_hash,
            "query_length": len(request.query),
            "market": request.market.model_dump(mode="json") if request.market else None,
            "constraints": request.constraints.model_dump(mode="json"),
            "response": response.model_dump(mode="json"),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")
