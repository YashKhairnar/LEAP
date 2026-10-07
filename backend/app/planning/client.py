from __future__ import annotations

import hashlib
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..models import PlannerRequest, PlannerResponse


class WorldModelUnavailable(RuntimeError):
    pass


def plan_next_action(
    request: PlannerRequest,
    observations: list[dict],
    learner_id: str,
) -> PlannerResponse:
    if os.getenv("WORLD_MODEL_ENABLED", "false").lower() != "true":
        raise WorldModelUnavailable("world model disabled for collection")
    service_url = os.getenv("WORLD_MODEL_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")
    if "://" not in service_url:
        service_url = f"http://{service_url}"
    token = os.getenv("WORLD_MODEL_SERVICE_TOKEN")
    payload = {
        **request.model_dump(mode="json"),
        "observations": observations[-20:],
        "observation_count": len(observations),
        "initial_state_seed": int.from_bytes(
            hashlib.sha256(f"{learner_id}:{request.session_id}".encode()).digest()[:8],
            "big",
        ) % (2**63 - 1),
    }
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    service_request = Request(
        f"{service_url}/predict-action",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(
            service_request,
            timeout=float(os.getenv("WORLD_MODEL_TIMEOUT_SECONDS", "30")),
        ) as response:
            body = response.read()
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise WorldModelUnavailable(
            f"world-model service returned {error.code}: {detail[:500]}"
        ) from error
    except (URLError, OSError, TimeoutError, ValueError) as error:
        raise WorldModelUnavailable(str(error)) from error
    try:
        return PlannerResponse.model_validate_json(body)
    except ValueError as error:
        raise WorldModelUnavailable("world-model service returned an invalid response") from error
