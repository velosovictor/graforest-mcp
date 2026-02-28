# ============================================================================
# GRAFOREST MCP - RATIONALBLOKS INFRASTRUCTURE CLIENT
# ============================================================================
# Copyright 2026 Graforest. All Rights Reserved.
#
# HTTP client for provisioning graph infrastructure via the PUBLIC
# RationalBloks MCP gateway. Graforest is a customer of RationalBloks —
# it uses the same public API that any external developer would use.
#
# Auth: Graforest SERVICE ACCOUNT key (rb_sk_...) via GRAFOREST_RB_API_KEY
# env var. Individual Graforest users never see this key.
#
# Endpoint: POST /api/mcp/execute with {"tool": "...", "arguments": {...}}
# Reference: rationalbloks-mcp/backend/client.py (LogicBlokClient)
# ============================================================================

import asyncio
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default endpoint — can be overridden via env var
RATIONALBLOKS_MCP_URL = os.environ.get(
    "RATIONALBLOKS_MCP_URL",
    "https://logicblok.rationalbloks.com",
)

__all__ = ["RBClient", "KNOWLEDGE_GRAPH_SCHEMA"]


# ============================================================================
# KNOWLEDGE GRAPH DEFAULT SCHEMA
# ============================================================================
# Used when auto-provisioning a new graph project for Graforest users.
# A flexible general-purpose schema that suits most knowledge graph use cases.

KNOWLEDGE_GRAPH_SCHEMA: dict[str, Any] = {
    "nodes": {
        "Topic": {
            "description": "A broad knowledge area",
            "flat_labels": ["Category"],
            "schema": {
                "name": {"type": "string", "required": True},
                "description": {"type": "string"},
            },
            "TechnicalTopic": {
                "description": "A technical/scientific topic",
                "flat_labels": ["Technical"],
                "schema": {
                    "domain": {"type": "string", "required": True},
                    "difficulty_level": {"type": "string"},
                },
                "ProgrammingLanguage": {
                    "description": "A programming language",
                    "flat_labels": ["Language"],
                    "schema": {
                        "paradigm": {"type": "string", "required": True},
                        "first_appeared": {"type": "integer"},
                        "typing": {"type": "string"},
                    },
                },
            },
        },
        "Article": {
            "description": "A written piece of content",
            "flat_labels": ["Document"],
            "schema": {
                "title": {"type": "string", "required": True},
                "abstract": {"type": "string", "required": True},
                "published_date": {"type": "date"},
                "doi": {"type": "string"},
                "url": {"type": "string"},
            },
        },
        "Author": {
            "description": "A content creator or researcher",
            "flat_labels": ["Person"],
            "schema": {
                "name": {"type": "string", "required": True},
                "affiliation": {"type": "string"},
                "orcid": {"type": "string"},
                "email": {"type": "string"},
            },
        },
        "Concept": {
            "description": "An abstract concept or idea",
            "flat_labels": ["Idea"],
            "schema": {
                "name": {"type": "string", "required": True},
                "definition": {"type": "string", "required": True},
                "aliases": {"type": "json"},
            },
        },
    },
    "relationships": {
        "AUTHORED": {
            "from": "Author",
            "to": "Article",
            "cardinality": "ONE_TO_MANY",
            "data_schema": {"contribution": {"type": "string"}},
        },
        "COVERS": {
            "from": "Article",
            "to": "Topic",
            "cardinality": "MANY_TO_MANY",
        },
        "REFERENCES": {
            "from": "Article",
            "to": "Article",
            "cardinality": "MANY_TO_MANY",
            "data_schema": {"context": {"type": "string"}},
        },
        "PREREQUISITE_OF": {
            "from": "Concept",
            "to": "Concept",
            "cardinality": "MANY_TO_MANY",
            "data_schema": {"strength": {"type": "string"}},
        },
        "DEFINES": {
            "from": "Article",
            "to": "Concept",
            "cardinality": "MANY_TO_MANY",
        },
    },
}


# ============================================================================
# RATIONALBLOKS CLIENT
# ============================================================================

class RBClient:
    """HTTP client for the public RationalBloks MCP gateway.

    Uses the Graforest SERVICE ACCOUNT key (rb_sk_...) — not per-user keys.
    This is the only place in the codebase that talks to RationalBloks.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("GRAFOREST_RB_API_KEY", "")
        if not self._api_key:
            raise RuntimeError(
                "No RationalBloks service account key — "
                "set GRAFOREST_RB_API_KEY environment variable"
            )
        self._client = httpx.AsyncClient(
            base_url=RATIONALBLOKS_MCP_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=120.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "RBClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def _execute(self, tool: str, arguments: dict | None = None) -> Any:
        """Execute an MCP tool via the public RationalBloks gateway."""
        payload = {"tool": tool, "arguments": arguments or {}}
        response = await self._client.post("/api/mcp/execute", json=payload)
        response.raise_for_status()
        result = response.json()

        if not result.get("success", False):
            error = result.get("error", "Unknown error")
            raise Exception(f"RationalBloks MCP error: {error}")

        return result.get("result")

    # ====================================================================
    # GRAPH PROJECT OPERATIONS
    # ====================================================================

    async def create_graph_project(
        self,
        name: str,
        schema: dict | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new graph project via RationalBloks."""
        args: dict[str, Any] = {
            "name": name,
            "schema": schema or KNOWLEDGE_GRAPH_SCHEMA,
        }
        if description:
            args["description"] = description
        return await self._execute("create_graph_project", args)

    async def deploy_graph_staging(self, project_id: str) -> dict[str, Any]:
        """Deploy a graph project to staging."""
        return await self._execute("deploy_graph_staging", {"project_id": project_id})

    async def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get status of a deployment job."""
        return await self._execute("get_job_status", {"job_id": job_id})

    async def get_graph_project_info(self, project_id: str) -> dict[str, Any]:
        """Get detailed info about a graph project."""
        return await self._execute("get_graph_project_info", {"project_id": project_id})

    async def get_graph_schema(self, project_id: str) -> dict[str, Any]:
        """Get the FULL graph schema (nodes, relationships, field types)."""
        return await self._execute("get_graph_schema", {"project_id": project_id})

    async def list_projects(self) -> list[dict[str, Any]]:
        """List all projects under the service account."""
        raw = await self._execute("list_projects")
        if isinstance(raw, dict):
            return raw.get("projects", [])
        return raw if isinstance(raw, list) else []

    async def delete_graph_project(self, project_id: str) -> dict[str, Any]:
        """Delete a graph project and all associated resources."""
        return await self._execute("delete_graph_project", {"project_id": project_id})

    # ====================================================================
    # PROVISIONING WORKFLOW
    # ====================================================================

    async def provision_graph_project(
        self,
        name: str,
        description: str | None = None,
        poll_interval: float = 3.0,
        max_wait: float = 300.0,
    ) -> dict[str, Any]:
        """Full provisioning: create → deploy → poll → return info.

        1. Create graph project with knowledge graph schema
        2. Deploy to staging
        3. Poll deployment job until complete
        4. Return project info with graph API URL
        """
        logger.info(f"Provisioning graph project: {name}")

        # Step 1: Create
        project = await self.create_graph_project(
            name=name,
            description=description or f"Graforest knowledge graph: {name}",
        )
        project_id = project.get("id") or project.get("project_id")
        if not project_id:
            raise Exception(f"create_graph_project returned no project ID: {project}")
        logger.info(f"Created graph project {project_id}: {name}")

        # Step 2: Deploy
        deploy_result = await self.deploy_graph_staging(project_id)
        job_id = deploy_result.get("job_id")
        if not job_id:
            raise Exception(f"deploy_graph_staging returned no job_id: {deploy_result}")
        logger.info(f"Deployment started, job_id={job_id}")

        # Step 3: Poll
        elapsed = 0.0
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            status = await self.get_job_status(job_id)
            job_status = status.get("status", "unknown")
            logger.debug(f"Job {job_id}: {job_status} ({elapsed:.0f}s)")

            if job_status == "completed":
                logger.info(f"Deployment completed for {project_id} ({elapsed:.0f}s)")
                break
            if job_status in ("failed", "error"):
                error = status.get("error", "Unknown deployment error")
                raise Exception(f"Deployment failed for {project_id}: {error}")
        else:
            raise Exception(
                f"Deployment timed out after {max_wait}s for {project_id}"
            )

        # Step 4: Return project info
        info = await self.get_graph_project_info(project_id)
        logger.info(f"Graph project ready: {info.get('project_code', project_id)}")
        return info
