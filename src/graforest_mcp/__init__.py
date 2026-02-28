# ============================================================================
# GRAFOREST MCP — Knowledge Graph Server
# ============================================================================
# Copyright 2026 Graforest. All Rights Reserved.
#
# Build, populate, and query Knowledge Graphs with AI. 13 tools for:
#   - Provisioning: 3 tools (create, list, delete knowledge graphs)
#   - Data Write: 2 tools (bulk create nodes, bulk create relationships)
#   - Data Read: 6 tools (search, traverse, list, get, schema, statistics)
#   - Ingestion: 1 tool (text → extraction instructions)
#   - Utility: 1 tool (fetch URL content)
#
# Usage:
#   export GRAFOREST_API_KEY=gf_sk_your_key_here
#   graforest-mcp
#
# Environment Variables:
#   GRAFOREST_API_KEY - Your Graforest API key (required for STDIO mode)
#   TRANSPORT         - Transport: stdio (default) or http
# ============================================================================

import os
import sys

# Version from package metadata
from importlib.metadata import version as _get_version
__version__ = _get_version("graforest-mcp")

# Public API
__all__ = [
    "__version__",
    "main",
]


def _validate_api_key(api_key: str | None, transport: str) -> str | None:
    """Validate API key for the given transport.
    HTTP mode: API key provided per-request (returns None).
    STDIO mode: API key required at startup (returns validated key).
    """
    if transport == "http":
        return None

    if not api_key:
        print("ERROR: GRAFOREST_API_KEY environment variable not set", file=sys.stderr)
        print("", file=sys.stderr)
        print("Get your API key from: https://graforest.ai/settings", file=sys.stderr)
        print("", file=sys.stderr)
        print("Then set it:", file=sys.stderr)
        print("  export GRAFOREST_API_KEY=gf_sk_your_key_here", file=sys.stderr)
        sys.exit(1)

    if not api_key.startswith("gf_sk_"):
        print("ERROR: Invalid API key format. Must start with 'gf_sk_'", file=sys.stderr)
        sys.exit(1)

    return api_key


def main() -> None:
    """Main entry point — runs the Graforest MCP server."""
    api_key = os.environ.get("GRAFOREST_API_KEY")
    transport = os.environ.get("TRANSPORT", "stdio").lower()
    http_mode = transport == "http"

    validated_key = _validate_api_key(api_key, transport)

    print(
        f"[graforest-mcp] Starting server (13 tools: "
        f"3 provisioning + 2 write + 6 read + 1 ingestion + 1 utility)...",
        file=sys.stderr,
    )

    try:
        from .backend import create_graforest_server
        server = create_graforest_server(api_key=validated_key, http_mode=http_mode)
        server.run(transport=transport)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
