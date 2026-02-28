# ============================================================================
# GRAFOREST MCP - BASE SERVER
# ============================================================================
# Copyright 2026 Graforest. All Rights Reserved.
#
# Base MCP server class for the Graforest knowledge graph tools.
# Symmetric with rationalbloks-mcp/core/server.py.
# ============================================================================

import json
import sys
from typing import Any, Callable

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
from mcp.types import (
    Tool,
    ToolAnnotations,
    TextContent,
    Prompt,
    PromptArgument,
    PromptMessage,
    GetPromptResult,
    Resource,
    Icon,
)
from starlette.requests import Request

from .auth import validate_api_key, extract_api_key_from_request, APIKeyCache
from .transport import run_stdio, run_http

__all__ = [
    "BaseMCPServer",
    "create_mcp_server",
]


# ============================================================================
# STATIC RESOURCE CONTENT
# ============================================================================

DOCS_GETTING_STARTED = """# Getting Started with Graforest MCP

## Quick Start

1. Get your API key from https://graforest.ai/settings
2. Set environment variable: export GRAFOREST_API_KEY=gf_sk_...
3. Run the server: uvx graforest-mcp

## Tools (13 total)

Graforest MCP provides 13 knowledge graph tools:

- **Provisioning** (3 tools): Create, list, delete knowledge graphs
- **Data Write** (2 tools): Bulk create nodes, bulk create relationships
- **Data Read** (6 tools): Search, traverse, list, get, schema, statistics
- **Ingestion** (1 tool): Text → extraction instructions (3-call workflow)
- **Utility** (1 tool): Fetch URL content for ingestion

## 3-Call Ingestion Workflow (Recommended)

1. `ingest_text_content(project_code, text)` → returns schema + instructions
2. Extract ALL entities and relationships from the text in one pass
3. `add_knowledge_nodes(project_code, entities)` → bulk create all nodes
4. `add_knowledge_relationships(project_code, relationships)` → bulk create all edges

## Need Help?

Visit https://graforest.ai/docs for full documentation.
"""

DOCS_KNOWLEDGE_GRAPH = """# Knowledge Graph Guide

## What is a Knowledge Graph?

A knowledge graph is a structured representation of facts:
- **Nodes** (entities): People, concepts, topics, articles
- **Relationships** (edges): Connections between entities

## Entity Types

Your graph schema defines available entity types. Common patterns:
- Topic, Concept, Article, Author, Person, Organization
- Each type has specific fields (name, description, etc.)

## Relationship Types

Defined in schema with from/to entity types:
- AUTHORED: Author → Article
- COVERS: Article → Topic
- PREREQUISITE_OF: Concept → Concept

## Best Practices

1. Use `get_knowledge_schema` first to see available types
2. Use kebab-case entity IDs: 'machine-learning', 'iron-fe'
3. Extract thoroughly — more entities = richer graph
4. Always create relationships between related entities
"""


def create_mcp_server(
    name: str,
    version: str,
    instructions: str,
) -> Server:
    """Create a configured MCP Server instance."""
    return Server(
        name=name,
        version=version,
        instructions=instructions,
        website_url="https://graforest.ai",
        icons=[
            Icon(src="https://graforest.ai/logo.svg", mimeType="image/svg+xml"),
            Icon(src="https://graforest.ai/logo.png", mimeType="image/png", sizes=["128x128"]),
        ],
    )


class BaseMCPServer:
    """Base MCP server with shared infrastructure.
    Provides: Server initialization, common handlers, transport layer, auth.
    Subclasses add: mode-specific tools and handlers.
    """

    def __init__(
        self,
        name: str,
        version: str,
        instructions: str,
        api_key: str | None = None,
        http_mode: bool = False,
    ) -> None:
        self.name = name
        self.version = version
        self.instructions = instructions
        self.http_mode = http_mode
        self._api_key_cache = APIKeyCache()

        # Validate API key for STDIO mode
        if not http_mode:
            is_valid, error = validate_api_key(api_key)
            if not is_valid:
                raise ValueError(error)
            self.api_key = api_key
        else:
            self.api_key = None

        # Create MCP server instance
        self.server = create_mcp_server(name, version, instructions)

        # Tools and handlers (set by subclass)
        self._tools: list[dict] = []
        self._tool_handlers: dict[str, Callable] = {}
        self._prompts: list[Prompt] = []
        self._prompt_handlers: dict[str, Callable] = {}

        # Resources
        self._static_resources: dict[str, str] = {
            "graforest://docs/getting-started": DOCS_GETTING_STARTED,
            "graforest://docs/knowledge-graph": DOCS_KNOWLEDGE_GRAPH,
        }

    def register_tools(self, tools: list[dict]) -> None:
        self._tools.extend(tools)

    def register_tool_handler(self, name: str, handler: Callable) -> None:
        self._tool_handlers[name] = handler

    def register_prompts(self, prompts: list[Prompt]) -> None:
        self._prompts.extend(prompts)

    def register_prompt_handler(self, name: str, handler: Callable) -> None:
        self._prompt_handlers[name] = handler

    def setup_handlers(self) -> None:
        """Set up all MCP protocol handlers. Call AFTER registering tools."""
        self._setup_tool_handlers()
        self._setup_prompt_handlers()
        self._setup_resource_handlers()

    def _setup_tool_handlers(self) -> None:
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            tools_list = []
            for tool in self._tools:
                annotations = None
                if "annotations" in tool:
                    ann = tool["annotations"]
                    annotations = ToolAnnotations(
                        readOnlyHint=ann.get("readOnlyHint"),
                        destructiveHint=ann.get("destructiveHint"),
                        idempotentHint=ann.get("idempotentHint"),
                        openWorldHint=ann.get("openWorldHint"),
                    )
                tool_obj = Tool(
                    name=tool["name"],
                    title=tool.get("title"),
                    description=tool["description"],
                    inputSchema=tool["inputSchema"],
                    annotations=annotations,
                )
                tools_list.append(tool_obj)
            return tools_list

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            valid_tools = [t["name"] for t in self._tools]
            if name not in valid_tools:
                raise ValueError(f"Unknown tool: {name}")

            handler = self._tool_handlers.get(name) or self._tool_handlers.get("*")
            if not handler:
                raise ValueError(f"No handler registered for tool: {name}")

            try:
                result = await handler(name, arguments)
                formatted = json.dumps(result, indent=2, default=str)
                return [TextContent(type="text", text=formatted)]
            except Exception as e:
                print(f"[graforest-mcp] Error in {name}: {e}", file=sys.stderr)
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    def _setup_prompt_handlers(self) -> None:
        @self.server.list_prompts()
        async def list_prompts() -> list[Prompt]:
            return self._prompts

        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
            handler = self._prompt_handlers.get(name)
            if not handler:
                raise ValueError(f"Unknown prompt: {name}")
            return handler(name, arguments)

    def _setup_resource_handlers(self) -> None:
        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            resources = []
            for uri, _ in self._static_resources.items():
                name = uri.split("/")[-1].replace("-", " ").title()
                resources.append(Resource(
                    uri=uri,
                    name=f"{name} Guide",
                    description=f"Documentation: {name}",
                    mimeType="text/markdown",
                ))
            return resources

        @self.server.read_resource()
        async def read_resource(uri) -> str:
            uri_str = str(uri)
            if uri_str in self._static_resources:
                return self._static_resources[uri_str]
            raise ValueError(f"Unknown resource: {uri_str}")

    def get_api_key_for_request(self) -> str | None:
        """Get API key for current request.
        STDIO mode: Returns stored API key.
        HTTP mode: Extracts from Authorization header.
        """
        if not self.http_mode:
            return self.api_key

        ctx = getattr(self.server, "request_context", None)
        if ctx is None:
            return None

        request = getattr(ctx, "request", None)
        if request is None or not isinstance(request, Request):
            return None

        return extract_api_key_from_request(request)

    def get_init_options(self) -> InitializationOptions:
        return InitializationOptions(
            server_name=self.name,
            server_version=self.version,
            capabilities=self.server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
            instructions=self.instructions,
            website_url="https://graforest.ai",
        )

    def run(self, transport: str = "stdio") -> None:
        """Run the MCP server with specified transport."""
        if transport == "http":
            run_http(
                server=self.server,
                name=self.name,
                version=self.version,
                description=self.instructions,
            )
        else:
            run_stdio(
                server=self.server,
                init_options=self.get_init_options(),
            )
