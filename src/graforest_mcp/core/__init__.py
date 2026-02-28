# ============================================================================
# GRAFOREST MCP - CORE MODULE
# ============================================================================
# Copyright 2026 Graforest. All Rights Reserved.
#
# Shared core components for the MCP server:
#   - Base MCP server class
#   - Transport layer (STDIO + HTTP)
#   - Authentication utilities
#
# ARCHITECTURE:
# GraforestMCPServer extends this core with 13 knowledge graph tools.
# Symmetric with rationalbloks-mcp/core.
# ============================================================================

from .auth import (
    validate_api_key,
    extract_api_key_from_request,
    APIKeyCache,
)
from .server import (
    BaseMCPServer,
    create_mcp_server,
)
from .transport import (
    run_stdio,
    run_http,
    create_http_app,
)

__all__ = [
    "validate_api_key",
    "extract_api_key_from_request",
    "APIKeyCache",
    "BaseMCPServer",
    "create_mcp_server",
    "run_stdio",
    "run_http",
    "create_http_app",
]
