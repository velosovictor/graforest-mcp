# ============================================================================
# GRAFOREST MCP - AUTHENTICATION UTILITIES
# ============================================================================
# Copyright 2026 Graforest. All Rights Reserved.
#
# Shared authentication logic for the MCP server.
# Follows OAuth2 Bearer Token pattern (RFC 6750).
#
# Symmetric with rationalbloks-mcp/core/auth.py.
# Key prefix: gf_sk_ (Graforest Secret Key)
# ============================================================================

from typing import Any
from starlette.requests import Request

__all__ = [
    "validate_api_key",
    "extract_api_key_from_request",
    "APIKeyCache",
]

# API key prefix — all Graforest keys start with this
API_KEY_PREFIX = "gf_sk_"
BEARER_PREFIX = "Bearer "


def validate_api_key(api_key: str | None) -> tuple[bool, str | None]:
    """Validate API key format.
    Returns: (is_valid, error_message).
    """
    if not api_key:
        return False, "API key is required"

    if not isinstance(api_key, str):
        return False, "API key must be a string"

    if not api_key.startswith(API_KEY_PREFIX):
        return False, f"Invalid API key format — must start with '{API_KEY_PREFIX}'"

    # Minimum length check (prefix + at least 20 chars)
    if len(api_key) < len(API_KEY_PREFIX) + 20:
        return False, "API key is too short"

    return True, None


def extract_api_key_from_request(request: Request) -> str | None:
    """Extract API key from HTTP Authorization header.
    Expected format: Authorization: Bearer gf_sk_...
    """
    if request is None:
        return None

    auth_header = request.headers.get("authorization", "")

    if not auth_header.startswith(BEARER_PREFIX):
        return None

    api_key = auth_header[len(BEARER_PREFIX):]

    is_valid, _ = validate_api_key(api_key)
    if not is_valid:
        return None

    return api_key


class APIKeyCache:
    """In-memory cache for validated API keys.
    Stores validation results to avoid repeated calls to auth server.
    Cache is per-server-instance (not persistent across restarts).
    Only stores key prefix (first 20 chars) as cache key for security.
    """

    def __init__(self, max_size: int = 100) -> None:
        self._cache: dict[str, dict[str, Any]] = {}
        self._max_size = max_size

    def _get_cache_key(self, api_key: str) -> str:
        return api_key[:20] if len(api_key) >= 20 else api_key

    def get(self, api_key: str) -> dict[str, Any] | None:
        cache_key = self._get_cache_key(api_key)
        return self._cache.get(cache_key)

    def set(self, api_key: str, user_info: dict[str, Any]) -> None:
        if len(self._cache) >= self._max_size:
            keys_to_remove = list(self._cache.keys())[: self._max_size // 2]
            for key in keys_to_remove:
                del self._cache[key]
        cache_key = self._get_cache_key(api_key)
        self._cache[cache_key] = user_info

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)
