# ============================================================================
# GRAFOREST MCP - TRANSPORT LAYER
# ============================================================================
# Copyright 2026 Graforest. All Rights Reserved.
#
# Shared transport implementations for STDIO and HTTP modes.
# Symmetric with rationalbloks-mcp/core/transport.py.
#
# DUAL TRANSPORT ARCHITECTURE:
# - STDIO:  Local development (Cursor, VS Code, Claude Desktop)
# - HTTP:   Cloud deployment (Smithery, Replit, web agents)
# ============================================================================

import asyncio
import contextlib
import os
import sys
from typing import Any, Callable
from collections.abc import AsyncIterator

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

__all__ = [
    "run_stdio",
    "run_http",
    "create_http_app",
]


# ============================================================================
# STDIO TRANSPORT - Local IDE Integration
# ============================================================================

def run_stdio(
    server: Server,
    init_options: InitializationOptions,
) -> None:
    """Run MCP server in STDIO mode for local IDEs."""
    asyncio.run(_stdio_async(server, init_options))


async def _stdio_async(
    server: Server,
    init_options: InitializationOptions,
) -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, init_options)


# ============================================================================
# HTTP TRANSPORT - Cloud/Smithery Deployment
# ============================================================================

def run_http(
    server: Server,
    name: str,
    version: str,
    description: str,
    server_card_builder: Callable[[], dict] | None = None,
) -> None:
    """Run MCP server in HTTP mode for cloud deployment."""
    import uvicorn

    app = create_http_app(server, name, version, description, server_card_builder)

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"[graforest-mcp] HTTP server starting on {host}:{port}", file=sys.stderr)
    print(f"[graforest-mcp] MCP endpoints:", file=sys.stderr)
    print(f"[graforest-mcp]   - http://{host}:{port}/sse (primary)", file=sys.stderr)
    print(f"[graforest-mcp]   - http://{host}:{port}/mcp (alternative)", file=sys.stderr)

    uvicorn.run(app, host=host, port=port, log_level="info")


def create_http_app(
    server: Server,
    name: str,
    version: str,
    description: str,
    server_card_builder: Callable[[], dict] | None = None,
) -> Any:
    """Create Starlette ASGI application for HTTP transport."""
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse
    from starlette.middleware.cors import CORSMiddleware
    from starlette.types import Receive, Scope, Send

    session_manager = StreamableHTTPSessionManager(
        app=server,
        json_response=True,
        stateless=True,
    )

    async def server_card(request):
        if server_card_builder:
            card = server_card_builder()
        else:
            card = _build_default_server_card(name, version, description)
        return JSONResponse(card)

    async def health(request):
        return JSONResponse({"status": "ok", "version": version})

    async def handle_streamable(scope: Scope, receive: Receive, send: Send):
        await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            yield

    app = Starlette(
        debug=False,
        routes=[
            Route("/.well-known/mcp/server-card.json", endpoint=server_card, methods=["GET"]),
            Route("/health", endpoint=health, methods=["GET"]),
            Mount("/sse", app=handle_streamable),
            Mount("/mcp", app=handle_streamable),
            Mount("/", app=handle_streamable),
        ],
        lifespan=lifespan,
    )

    app = CORSMiddleware(
        app,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )

    return app


def _build_default_server_card(name: str, version: str, description: str) -> dict:
    return {
        "name": name,
        "displayName": "Graforest MCP",
        "version": version,
        "description": description,
        "vendor": "Graforest",
        "homepage": "https://graforest.ai",
        "icon": "https://graforest.ai/logo.svg",
        "documentation": "https://graforest.ai/docs",
        "capabilities": {
            "tools": True,
            "resources": True,
            "prompts": True,
        },
        "authentication": {
            "type": "bearer",
            "scheme": "Bearer",
            "description": "Graforest API Key (format: gf_sk_...)",
            "header": "Authorization: Bearer gf_sk_...",
        },
        "configSchema": {
            "type": "object",
            "title": "Graforest Configuration",
            "required": [],
            "properties": {
                "apiKey": {
                    "type": "string",
                    "title": "API Key",
                    "description": "Your Graforest API key (get from https://graforest.ai/settings)",
                    "default": "",
                    "x-from": {"header": "authorization"},
                }
            },
        },
    }
