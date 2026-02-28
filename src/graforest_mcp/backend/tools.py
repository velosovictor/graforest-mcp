# ============================================================================
# GRAFOREST MCP - KNOWLEDGE GRAPH TOOLS
# ============================================================================
# Copyright 2026 Graforest. All Rights Reserved.
#
# 13 Knowledge Graph tools:
#
# PROVISIONING (3):
#   create_knowledge_project     — Provision a new knowledge graph
#   list_knowledge_projects      — List provisioned graph projects
#   delete_knowledge_project     — Delete a graph project
#
# DATA WRITE (2):
#   add_knowledge_nodes          — Bulk create entities (LLM provides data)
#   add_knowledge_relationships  — Bulk create relationships
#
# DATA READ (6):
#   search_knowledge_graph       — Full-text search across graph nodes
#   get_knowledge_schema         — Get entity types, relationship types, fields
#   get_knowledge_statistics     — Get node/relationship counts by type
#   traverse_knowledge_graph     — Walk connections from a starting node
#   list_knowledge_entities      — List entities of a specific type
#   get_knowledge_entity         — Get a single entity by type and ID
#
# INGESTION (1):
#   ingest_text_content          — Prepare text for bulk extraction workflow
#
# UTILITY (1):
#   fetch_url_content            — Scrape URL for clean text
#
# ARCHITECTURE:
#   The LLM IS the intelligence. It reads content, extracts entities, and
#   calls add_knowledge_nodes/relationships. Graforest is the data layer.
# ============================================================================

import logging
from typing import Any

from mcp.types import (
    Prompt,
    PromptArgument,
    PromptMessage,
    GetPromptResult,
    TextContent,
)

from .. import __version__
from ..core import BaseMCPServer
from .graph_client import GraphClient
from .rb_client import RBClient

logger = logging.getLogger(__name__)

__all__ = [
    "GRAFOREST_TOOLS",
    "GRAFOREST_PROMPTS",
    "GraforestMCPServer",
    "create_graforest_server",
]


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

GRAFOREST_TOOLS: list[dict[str, Any]] = [
    # ================================================================
    # PROVISIONING (3 tools)
    # ================================================================
    {
        "name": "create_knowledge_project",
        "title": "Create Knowledge Graph Project",
        "description": (
            "Provision a new knowledge graph project. Creates a Neo4j graph database "
            "with a knowledge-optimized schema (Topics, Articles, Authors, Concepts) "
            "and deploys it to staging. May take 30-60 seconds."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project name (e.g., 'AI Research Papers')",
                },
                "description": {
                    "type": "string",
                    "description": "Optional project description",
                },
            },
            "required": ["name"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    },
    {
        "name": "list_knowledge_projects",
        "title": "List Knowledge Graph Projects",
        "description": "List all graph projects. Shows project IDs, names, codes, and status.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "delete_knowledge_project",
        "title": "Delete Knowledge Graph Project",
        "description": (
            "Delete a graph project and ALL its data. DESTRUCTIVE — cannot be undone."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project ID to delete (UUID)",
                },
            },
            "required": ["project_id"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    },

    # ================================================================
    # DATA WRITE (2 tools)
    # ================================================================
    {
        "name": "add_knowledge_nodes",
        "title": "Add Knowledge Nodes",
        "description": (
            "Bulk create entities in the knowledge graph. The LLM extracts entities from "
            "content and provides them here. Each entity needs an entity_id (kebab-case), "
            "entity_type (matching schema — e.g., 'Topic', 'Article', 'Author', 'Concept'), "
            "and properties dict matching that type's schema fields.\n\n"
            "Use get_knowledge_schema first to see available entity types and their fields."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_code": {
                    "type": "string",
                    "description": "Project code (e.g., 'abc12345') — from list_knowledge_projects",
                },
                "entities": {
                    "type": "array",
                    "description": "Array of entities to create",
                    "items": {
                        "type": "object",
                        "properties": {
                            "entity_id": {
                                "type": "string",
                                "description": "Unique ID (kebab-case, e.g., 'machine-learning')",
                            },
                            "entity_type": {
                                "type": "string",
                                "description": "Schema entity type (e.g., 'Topic', 'Article')",
                            },
                            "properties": {
                                "type": "object",
                                "description": "Entity properties matching the schema fields",
                            },
                        },
                        "required": ["entity_id", "entity_type", "properties"],
                    },
                },
                "environment": {
                    "type": "string",
                    "description": "Target environment",
                    "enum": ["staging", "production"],
                    "default": "staging",
                },
            },
            "required": ["project_code", "entities"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    },
    {
        "name": "add_knowledge_relationships",
        "title": "Add Knowledge Relationships",
        "description": (
            "Bulk create relationships between entities in the knowledge graph. "
            "Each relationship needs from_id, to_id (matching existing entity_ids), "
            "rel_type (matching schema — e.g., 'AUTHORED', 'COVERS', 'REFERENCES'), "
            "and optional properties.\n\n"
            "Use get_knowledge_schema first to see available relationship types."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_code": {
                    "type": "string",
                    "description": "Project code (e.g., 'abc12345') — from list_knowledge_projects",
                },
                "relationships": {
                    "type": "array",
                    "description": "Array of relationships to create",
                    "items": {
                        "type": "object",
                        "properties": {
                            "from_id": {
                                "type": "string",
                                "description": "Source entity_id",
                            },
                            "to_id": {
                                "type": "string",
                                "description": "Target entity_id",
                            },
                            "rel_type": {
                                "type": "string",
                                "description": "Relationship type (e.g., 'AUTHORED', 'COVERS')",
                            },
                            "properties": {
                                "type": "object",
                                "description": "Optional relationship properties",
                            },
                        },
                        "required": ["from_id", "to_id", "rel_type"],
                    },
                },
                "environment": {
                    "type": "string",
                    "description": "Target environment",
                    "enum": ["staging", "production"],
                    "default": "staging",
                },
            },
            "required": ["project_code", "relationships"],
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    },

    # ================================================================
    # DATA READ (6 tools)
    # ================================================================
    {
        "name": "search_knowledge_graph",
        "title": "Search Knowledge Graph",
        "description": (
            "Full-text search across all string properties in the knowledge graph. "
            "Returns matching nodes with their types, properties, and relevance scores."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_code": {
                    "type": "string",
                    "description": "Project code — from list_knowledge_projects",
                },
                "query": {
                    "type": "string",
                    "description": "Search text (e.g., 'machine learning', 'Python')",
                },
                "environment": {
                    "type": "string",
                    "enum": ["staging", "production"],
                    "default": "staging",
                },
            },
            "required": ["project_code", "query"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "get_knowledge_schema",
        "title": "Get Knowledge Graph Schema",
        "description": (
            "Get the full schema — entity types with fields, relationship types with "
            "from/to mappings. CALL THIS FIRST before adding nodes or relationships "
            "to understand what types and fields are available."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_code": {
                    "type": "string",
                    "description": "Project code — from list_knowledge_projects",
                },
                "environment": {
                    "type": "string",
                    "enum": ["staging", "production"],
                    "default": "staging",
                },
            },
            "required": ["project_code"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "get_knowledge_statistics",
        "title": "Get Knowledge Graph Statistics",
        "description": (
            "Get node/relationship counts broken down by type. "
            "Useful for understanding the graph's size and composition."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_code": {
                    "type": "string",
                    "description": "Project code — from list_knowledge_projects",
                },
                "environment": {
                    "type": "string",
                    "enum": ["staging", "production"],
                    "default": "staging",
                },
            },
            "required": ["project_code"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "traverse_knowledge_graph",
        "title": "Traverse Knowledge Graph",
        "description": (
            "Walk the graph from a starting entity, following relationships up to "
            "a specified depth. Returns connected nodes and relationships."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_code": {
                    "type": "string",
                    "description": "Project code — from list_knowledge_projects",
                },
                "start_entity_type": {
                    "type": "string",
                    "description": "Entity type of the starting node (e.g., 'Topic')",
                },
                "start_entity_id": {
                    "type": "string",
                    "description": "Entity ID of the starting node",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum traversal depth (default 3, max 5)",
                    "default": 3,
                },
                "direction": {
                    "type": "string",
                    "enum": ["outgoing", "incoming", "both"],
                    "default": "both",
                },
                "environment": {
                    "type": "string",
                    "enum": ["staging", "production"],
                    "default": "staging",
                },
            },
            "required": ["project_code", "start_entity_type", "start_entity_id"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "list_knowledge_entities",
        "title": "List Knowledge Entities",
        "description": (
            "List entities of a specific type. "
            "Use get_knowledge_schema first to see available entity types."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_code": {
                    "type": "string",
                    "description": "Project code — from list_knowledge_projects",
                },
                "entity_type": {
                    "type": "string",
                    "description": "Entity type to list (e.g., 'Topic', 'Article')",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 50)",
                    "default": 50,
                },
                "offset": {
                    "type": "integer",
                    "description": "Offset for pagination",
                    "default": 0,
                },
                "environment": {
                    "type": "string",
                    "enum": ["staging", "production"],
                    "default": "staging",
                },
            },
            "required": ["project_code", "entity_type"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "get_knowledge_entity",
        "title": "Get Knowledge Entity",
        "description": "Get a single entity by type and ID, with all properties.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_code": {
                    "type": "string",
                    "description": "Project code — from list_knowledge_projects",
                },
                "entity_type": {
                    "type": "string",
                    "description": "Entity type (e.g., 'Topic', 'Article')",
                },
                "entity_id": {
                    "type": "string",
                    "description": "Entity ID",
                },
                "environment": {
                    "type": "string",
                    "enum": ["staging", "production"],
                    "default": "staging",
                },
            },
            "required": ["project_code", "entity_type", "entity_id"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },

    # ================================================================
    # INGESTION (1 tool)
    # ================================================================
    {
        "name": "ingest_text_content",
        "title": "Ingest Text Content",
        "description": (
            "BATCH INGESTION — the fast way to populate a knowledge graph.\n\n"
            "Provide a large block of text (up to 500k chars) and the project code. "
            "This tool fetches the graph schema and returns structured extraction "
            "instructions. Then call add_knowledge_nodes and add_knowledge_relationships "
            "with the extracted data.\n\n"
            "3-CALL WORKFLOW:\n"
            "  1. ingest_text_content(project_code, text) → schema + instructions\n"
            "  2. add_knowledge_nodes(project_code, entities) → bulk create nodes\n"
            "  3. add_knowledge_relationships(project_code, relationships) → bulk create edges\n\n"
            "This replaces per-entity approach. Extract EVERYTHING from the text "
            "in one pass, then write it all in two bulk calls."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_code": {
                    "type": "string",
                    "description": "Project code (e.g., 'abc12345') — from list_knowledge_projects",
                },
                "text_content": {
                    "type": "string",
                    "description": (
                        "The full text to extract knowledge from (up to 500k chars). "
                        "Can be a book chapter, article, lecture notes, etc."
                    ),
                },
                "source_title": {
                    "type": "string",
                    "description": "Optional title/name of the source material",
                },
                "source_url": {
                    "type": "string",
                    "description": "Optional URL of the source material",
                },
                "environment": {
                    "type": "string",
                    "description": "Target environment",
                    "enum": ["staging", "production"],
                    "default": "staging",
                },
            },
            "required": ["project_code", "text_content"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },

    # ================================================================
    # UTILITY (1 tool)
    # ================================================================
    {
        "name": "fetch_url_content",
        "title": "Fetch URL Content",
        "description": (
            "Scrape a URL and extract clean text content. Returns the text for "
            "the LLM to read, extract entities from, and then call "
            "add_knowledge_nodes/relationships. Also returns metadata (title, author, date)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to scrape",
                },
            },
            "required": ["url"],
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },
]


# ============================================================================
# PROMPT DEFINITIONS
# ============================================================================

GRAFOREST_PROMPTS: list[Prompt] = [
    Prompt(
        name="ingest-content",
        description=(
            "Ingest text content into a knowledge graph using the 3-call workflow. "
            "Extracts entities and relationships from the provided text."
        ),
        arguments=[
            PromptArgument(
                name="project_code",
                description="Project code for the target knowledge graph",
                required=True,
            ),
            PromptArgument(
                name="text",
                description="Text content to extract knowledge from",
                required=True,
            ),
        ],
    ),
    Prompt(
        name="explore-graph",
        description=(
            "Explore a knowledge graph — get statistics, search for concepts, "
            "and traverse connections."
        ),
        arguments=[
            PromptArgument(
                name="project_code",
                description="Project code for the knowledge graph to explore",
                required=True,
            ),
            PromptArgument(
                name="topic",
                description="Optional topic or concept to start exploring from",
                required=False,
            ),
        ],
    ),
]


# ============================================================================
# MAX CONTENT LENGTH
# ============================================================================

MAX_CONTENT_LENGTH = 500_000  # 500k chars


# ============================================================================
# GRAFOREST MCP SERVER
# ============================================================================

class GraforestMCPServer(BaseMCPServer):
    """Graforest MCP server with 13 knowledge graph tools.

    Extends BaseMCPServer with:
    - GraphClient for data operations (read/write against deployed Graph APIs)
    - RBClient for infrastructure provisioning (via RationalBloks service account)
    - 13 tools: 3 provisioning + 2 write + 6 read + 1 ingestion + 1 utility
    - 2 prompts: ingest-content, explore-graph
    """

    INSTRUCTIONS = """Graforest MCP Server — Knowledge Graph Data Operations

Store, search, and explore Knowledge Graphs. NO AI inside — YOU are the intelligence.

FAST INGESTION (recommended — 3 tool calls):
1. ingest_text_content(project_code, text) → returns schema + extraction instructions
2. Extract ALL entities and relationships from the text in one pass
3. add_knowledge_nodes(project_code, entities) → bulk create all nodes
4. add_knowledge_relationships(project_code, relationships) → bulk create all edges

EXPLORATION:
- search_knowledge_graph → full-text search across all properties
- traverse_knowledge_graph → walk connections from a node
- list_knowledge_entities / get_knowledge_entity → read data

MANAGEMENT:
- list_knowledge_projects → find your graph
- create_knowledge_project → provision a new graph
- get_knowledge_schema → see entity types and fields

13 tools: 3 provisioning + 2 data write + 6 read + 1 ingestion + 1 utility"""

    def __init__(
        self,
        api_key: str | None = None,
        http_mode: bool = False,
    ) -> None:
        super().__init__(
            name="graforest",
            version=__version__,
            instructions=self.INSTRUCTIONS,
            api_key=api_key,
            http_mode=http_mode,
        )

        # HTTP clients — created lazily per request
        self._graph_client = GraphClient()

        # Register tools, prompts, handlers
        self.register_tools(GRAFOREST_TOOLS)
        self.register_prompts(GRAFOREST_PROMPTS)
        self.register_tool_handler("*", self._handle_tool)

        self.register_prompt_handler("ingest-content", self._handle_ingest_prompt)
        self.register_prompt_handler("explore-graph", self._handle_explore_prompt)

        # Set up MCP protocol handlers
        self.setup_handlers()

    def _get_rb_client(self) -> RBClient:
        """Get RBClient using the Graforest service account key."""
        return RBClient()

    def _get_auth_token(self) -> str:
        """Get the auth token for Graph API calls.

        In STDIO mode: uses the Graforest API key as a bearer token.
        In HTTP mode: extracts from the incoming request's Authorization header.

        Note: Graph APIs validate JWTs via DataBlok. In production, this will
        use a service-to-service token obtained from the Graforest auth system.
        For now, we forward the user's API key / session token.
        """
        api_key = self.get_api_key_for_request()
        if not api_key:
            raise ValueError("No authentication token available")
        return api_key

    # ====================================================================
    # TOOL HANDLER — routes all 13 tools
    # ====================================================================

    async def _handle_tool(self, name: str, arguments: dict) -> Any:
        """Route tool calls to the appropriate handler."""

        # ============================================================
        # PROVISIONING (via RationalBloks service account)
        # ============================================================

        if name == "create_knowledge_project":
            async with self._get_rb_client() as rb:
                result = await rb.provision_graph_project(
                    name=arguments["name"],
                    description=arguments.get("description"),
                )
            return {
                "project_id": result.get("id") or result.get("project_id"),
                "project_code": result.get("project_code"),
                "name": result.get("name"),
                "status": "deployed",
                "message": "Knowledge graph created and deployed to staging",
                "graph_api_url": result.get("staging_url") or result.get("graph_api_url"),
            }

        if name == "list_knowledge_projects":
            async with self._get_rb_client() as rb:
                projects = await rb.list_projects()
            graph_projects = [
                p for p in projects
                if p.get("project_type", "graph") != "relational"
            ]
            return {
                "projects": [
                    {
                        "project_id": p.get("id") or p.get("project_id"),
                        "name": p.get("name"),
                        "project_code": p.get("project_code"),
                        "status": p.get("status"),
                        "created_at": p.get("created_at"),
                    }
                    for p in graph_projects
                ],
                "count": len(graph_projects),
            }

        if name == "delete_knowledge_project":
            async with self._get_rb_client() as rb:
                await rb.delete_graph_project(arguments["project_id"])
            return {
                "project_id": arguments["project_id"],
                "status": "deleted",
                "message": "Graph project and all data permanently deleted",
            }

        # ============================================================
        # DATA WRITE
        # ============================================================

        if name == "add_knowledge_nodes":
            token = self._get_auth_token()
            env = arguments.get("environment", "staging")
            result = await self._graph_client.bulk_create_entities(
                project_code=arguments["project_code"],
                environment=env,
                token=token,
                entities=arguments["entities"],
            )
            total = sum(result.values())
            return {
                "created": result,
                "total_created": total,
                "message": f"Created {total} nodes across {len(result)} types",
            }

        if name == "add_knowledge_relationships":
            token = self._get_auth_token()
            env = arguments.get("environment", "staging")
            result = await self._graph_client.bulk_create_relationships(
                project_code=arguments["project_code"],
                environment=env,
                token=token,
                relationships=arguments["relationships"],
            )
            total = sum(result.values())
            return {
                "created": result,
                "total_created": total,
                "message": f"Created {total} relationships across {len(result)} types",
            }

        # ============================================================
        # DATA READ
        # ============================================================

        if name == "search_knowledge_graph":
            token = self._get_auth_token()
            env = arguments.get("environment", "staging")
            return await self._graph_client.search_text(
                project_code=arguments["project_code"],
                environment=env,
                token=token,
                query=arguments["query"],
            )

        if name == "get_knowledge_schema":
            token = self._get_auth_token()
            env = arguments.get("environment", "staging")
            return await self._graph_client.get_schema(
                project_code=arguments["project_code"],
                environment=env,
                token=token,
            )

        if name == "get_knowledge_statistics":
            token = self._get_auth_token()
            env = arguments.get("environment", "staging")
            return await self._graph_client.get_statistics(
                project_code=arguments["project_code"],
                environment=env,
                token=token,
            )

        if name == "traverse_knowledge_graph":
            token = self._get_auth_token()
            env = arguments.get("environment", "staging")
            max_depth = min(arguments.get("max_depth", 3), 5)
            return await self._graph_client.traverse(
                project_code=arguments["project_code"],
                environment=env,
                token=token,
                start_entity_type=arguments["start_entity_type"],
                start_entity_id=arguments["start_entity_id"],
                max_depth=max_depth,
                direction=arguments.get("direction", "both"),
            )

        if name == "list_knowledge_entities":
            token = self._get_auth_token()
            env = arguments.get("environment", "staging")
            result = await self._graph_client.list_entities(
                project_code=arguments["project_code"],
                environment=env,
                token=token,
                entity_type=arguments["entity_type"],
                limit=arguments.get("limit", 50),
                offset=arguments.get("offset", 0),
            )
            return {"entities": result, "count": len(result)}

        if name == "get_knowledge_entity":
            token = self._get_auth_token()
            env = arguments.get("environment", "staging")
            return await self._graph_client.get_entity(
                project_code=arguments["project_code"],
                environment=env,
                token=token,
                entity_type=arguments["entity_type"],
                entity_id=arguments["entity_id"],
            )

        # ============================================================
        # INGESTION
        # ============================================================

        if name == "ingest_text_content":
            token = self._get_auth_token()
            text = arguments["text_content"]
            project_code = arguments["project_code"]
            env = arguments.get("environment", "staging")
            source_title = arguments.get("source_title", "")
            source_url = arguments.get("source_url", "")

            if not text or len(text.strip()) < 50:
                raise ValueError("Text content too short — provide at least 50 characters")
            if len(text) > MAX_CONTENT_LENGTH:
                raise ValueError(
                    f"Text content too large ({len(text):,} chars). "
                    f"Maximum is {MAX_CONTENT_LENGTH:,} chars. "
                    f"Split into smaller chunks and call ingest_text_content multiple times."
                )

            # Fetch the project's graph schema
            schema = await self._graph_client.get_schema(
                project_code=project_code,
                environment=env,
                token=token,
            )

            # Build extraction guide from schema
            entity_types = {}
            for key, info in schema.get("entities", {}).items():
                entity_types[key] = {"path": info.get("path", key)}

            relationship_types = {}
            for key, info in schema.get("relationships", {}).items():
                relationship_types[key] = {
                    "type_name": info.get("type_name", key.upper()),
                    "from": info.get("from_path", ""),
                    "to": info.get("to_path", ""),
                }

            # Try to get full schema definition (has field-level details)
            field_guide: dict[str, Any] = {}
            try:
                async with self._get_rb_client() as rb:
                    projects = await rb.list_projects()
                    project = next(
                        (p for p in projects if p.get("project_code") == project_code),
                        None,
                    )
                    if project:
                        pid = project.get("id") or project.get("project_id")
                        if pid:
                            full_schema = await rb.get_graph_schema(pid)
                            if full_schema and "nodes" in full_schema:
                                self._extract_field_guide(full_schema["nodes"], field_guide)
            except Exception as e:
                logger.debug(f"Could not fetch full schema for extraction guide: {e}")

            char_count = len(text)
            word_count = len(text.split())

            return {
                "status": "ready_for_extraction",
                "project_code": project_code,
                "source": {
                    "title": source_title,
                    "url": source_url,
                    "char_count": char_count,
                    "word_count": word_count,
                    "estimated_tokens": char_count // 4,
                },
                "schema": {
                    "entity_types": entity_types,
                    "relationship_types": relationship_types,
                    "field_details": field_guide or "Use get_knowledge_schema for field details",
                },
                "extraction_instructions": (
                    f"Extract ALL entities and relationships from the provided text.\n\n"
                    f"ENTITY TYPES available: {', '.join(entity_types.keys())}\n"
                    f"RELATIONSHIP TYPES available: {', '.join(relationship_types.keys())}\n\n"
                    f"RULES:\n"
                    f"1. Use kebab-case entity_ids (e.g., 'machine-learning', 'iron-fe')\n"
                    f"2. Entity types must match the schema keys exactly (lowercase)\n"
                    f"3. Include ALL required fields for each entity type\n"
                    f"4. Extract as many entities as the text supports — be thorough\n"
                    f"5. Create relationships between related entities\n"
                    f"6. Relationship from_id and to_id must match entity_ids you created\n\n"
                    f"NEXT STEPS:\n"
                    f"1. Process the text and extract entities + relationships\n"
                    f"2. Call add_knowledge_nodes with ALL extracted entities\n"
                    f"3. Call add_knowledge_relationships with ALL extracted relationships"
                ),
            }

        # ============================================================
        # UTILITY
        # ============================================================

        if name == "fetch_url_content":
            return await self._fetch_url(arguments["url"])

        raise ValueError(f"Unknown tool: {name}")

    # ====================================================================
    # HELPER METHODS
    # ====================================================================

    @staticmethod
    def _extract_field_guide(
        nodes_schema: dict[str, Any],
        field_guide: dict[str, Any],
    ) -> None:
        """Recursively extract field info from the full graph schema."""
        for key, val in nodes_schema.items():
            if isinstance(val, dict) and "schema" in val:
                fields = {}
                for fname, fdef in val["schema"].items():
                    ftype = fdef.get("type", "string")
                    req = " (REQUIRED)" if fdef.get("required") else ""
                    fields[fname] = f"{ftype}{req}"
                field_guide[key.lower()] = fields
                # Recurse for nested entity types
                for nested_key, nested_val in val.items():
                    if isinstance(nested_val, dict) and "schema" in nested_val:
                        GraforestMCPServer._extract_field_guide(
                            {nested_key: nested_val}, field_guide,
                        )

    @staticmethod
    async def _fetch_url(url: str) -> dict[str, Any]:
        """Fetch and clean text from a URL."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")

            if "text/html" in content_type:
                # Basic HTML → text extraction
                html = resp.text
                # Strip tags (simple approach — no dependency on beautifulsoup)
                import re
                # Remove script/style blocks
                text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
                # Remove HTML tags
                text = re.sub(r"<[^>]+>", " ", text)
                # Collapse whitespace
                text = re.sub(r"\s+", " ", text).strip()
            else:
                text = resp.text

            return {
                "text": text[:MAX_CONTENT_LENGTH],
                "char_count": len(text[:MAX_CONTENT_LENGTH]),
                "metadata": {
                    "content_type": content_type,
                    "status_code": resp.status_code,
                },
                "source_url": url,
            }

    # ====================================================================
    # PROMPT HANDLERS
    # ====================================================================

    def _handle_ingest_prompt(
        self, name: str, arguments: dict[str, str] | None,
    ) -> GetPromptResult:
        project_code = arguments.get("project_code", "") if arguments else ""
        text = arguments.get("text", "") if arguments else ""

        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=(
                            f"Ingest the following content into knowledge graph '{project_code}'.\n\n"
                            f"Use the 3-call workflow:\n"
                            f"1. Call ingest_text_content with the text below\n"
                            f"2. Extract ALL entities and relationships from it\n"
                            f"3. Call add_knowledge_nodes with all entities\n"
                            f"4. Call add_knowledge_relationships with all relationships\n\n"
                            f"Be thorough — extract every entity and connection you can find.\n\n"
                            f"---\n\n{text}"
                        ),
                    ),
                )
            ]
        )

    def _handle_explore_prompt(
        self, name: str, arguments: dict[str, str] | None,
    ) -> GetPromptResult:
        project_code = arguments.get("project_code", "") if arguments else ""
        topic = arguments.get("topic", "") if arguments else ""

        steps = (
            f"Explore knowledge graph '{project_code}':\n\n"
            f"1. Call get_knowledge_statistics to see what's in the graph\n"
            f"2. Call get_knowledge_schema to understand the data model\n"
        )
        if topic:
            steps += (
                f"3. Call search_knowledge_graph for '{topic}'\n"
                f"4. Pick an interesting result and call traverse_knowledge_graph\n"
                f"5. Summarize what you found and the connections\n"
            )
        else:
            steps += (
                f"3. List entities for the most populated type\n"
                f"4. Pick an interesting entity and traverse its connections\n"
                f"5. Summarize the graph's contents and structure\n"
            )

        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=steps),
                )
            ]
        )


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_graforest_server(
    api_key: str | None = None,
    http_mode: bool = False,
) -> GraforestMCPServer:
    """Factory function to create a Graforest MCP server."""
    return GraforestMCPServer(api_key=api_key, http_mode=http_mode)
