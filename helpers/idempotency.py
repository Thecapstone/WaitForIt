"""Small response cache helpers for idempotent API actions."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from django.core.cache import cache
from rest_framework.response import Response


def _json_default(value: Any) -> str:
    return str(value)


def request_fingerprint(request, scope: str, *parts: Any) -> str:
    """Build a stable cache key for a request body and route context."""
    explicit_key = request.headers.get("Idempotency-Key")
    user_id = getattr(getattr(request, "user", None), "id", None) or "anonymous"

    if explicit_key:
        raw = f"{scope}:{user_id}:{explicit_key}"
    else:
        body = {
            "method": request.method,
            "path": request.path,
            "data": request.data,
            "query": request.query_params,
            "parts": parts,
        }
        raw = json.dumps(body, sort_keys=True, default=_json_default)
        raw = f"{scope}:{user_id}:{raw}"

    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"idempotency:{scope}:{digest}"


def cached_response(key: str) -> Response | None:
    cached = cache.get(key)
    if not cached:
        return None
    return Response(cached["data"], status=cached["status"])


def remember_response(key: str, response: Response, timeout: int = 900) -> Response:
    if 200 <= response.status_code < 500:
        cache.set(
            key,
            {"data": response.data, "status": response.status_code},
            timeout=timeout,
        )
    return response
