# ============================================================================
# GRAFOREST MCP - GRAPH API CLIENT
# ============================================================================
# Copyright 2026 Graforest. All Rights Reserved.
#
# HTTP client for interacting with deployed Graph APIs (Neo4j).
# Handles data operations: CRUD, search, traverse, bulk write.
#
# NORMALIZATION:
#   Graph API returns entity_id, hierarchical_path, rel_id, rel_type.
#   This client normalizes for the MCP consumer:
#     - entity_id → id
#     - hierarchical_path → labels array
#     - rel_id → id, rel_type → type
# ============================================================================

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Graph API URL patterns
GRAPH_API_STAGING_PATTERN = "https://{project_code}-staging.rationalbloks.com"
GRAPH_API_PRODUCTION_PATTERN = "https://{project_code}.rationalbloks.com"

# Bulk operation batch size
MAX_BULK_SIZE = 500

__all__ = ["GraphClient"]


class GraphClient:
    """Async HTTP client for customer-deployed Graph APIs.

    Uses the Graforest service account's JWT (forwarded from the gateway)
    to authenticate against Graph API endpoints.
    """

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @staticmethod
    def _resolve_url(project_code: str, environment: str = "staging") -> str:
        code = project_code.lower().replace("_", "-")
        if environment == "production":
            return GRAPH_API_PRODUCTION_PATTERN.format(project_code=code)
        return GRAPH_API_STAGING_PATTERN.format(project_code=code)

    def _headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    # ====================================================================
    # SCHEMA & STATISTICS
    # ====================================================================

    async def get_schema(
        self, project_code: str, environment: str, token: str,
    ) -> dict[str, Any]:
        client = await self._get_client()
        base = self._resolve_url(project_code, environment)
        resp = await client.get(f"{base}/schema", headers=self._headers(token))
        resp.raise_for_status()
        return resp.json()

    async def get_statistics(
        self, project_code: str, environment: str, token: str,
    ) -> dict[str, Any]:
        client = await self._get_client()
        base = self._resolve_url(project_code, environment)
        resp = await client.get(
            f"{base}/api/v1/data/stats", headers=self._headers(token),
        )
        resp.raise_for_status()
        return resp.json()

    # ====================================================================
    # READ OPERATIONS
    # ====================================================================

    async def search_text(
        self, project_code: str, environment: str, token: str, query: str,
    ) -> dict[str, Any]:
        """Full-text search. Returns normalized {nodes, total, query}."""
        client = await self._get_client()
        base = self._resolve_url(project_code, environment)
        resp = await client.post(
            f"{base}/api/v1/data/search/text",
            json={"query": query},
            headers=self._headers(token),
        )
        resp.raise_for_status()
        data = resp.json()
        nodes = [self._normalize_node(n) for n in data.get("nodes", [])]
        return {
            "nodes": nodes,
            "total": data.get("count", len(nodes)),
            "query": data.get("query", query),
        }

    async def traverse(
        self,
        project_code: str,
        environment: str,
        token: str,
        start_entity_type: str,
        start_entity_id: str,
        max_depth: int = 3,
        direction: str = "both",
    ) -> dict[str, Any]:
        """Traverse graph. Returns normalized {nodes, relationships, depth}."""
        client = await self._get_client()
        base = self._resolve_url(project_code, environment)
        headers = self._headers(token)

        resp = await client.post(
            f"{base}/api/v1/data/traverse",
            json={
                "start_entity_type": start_entity_type.lower(),
                "start_entity_id": start_entity_id,
                "max_depth": max_depth,
                "direction": direction,
            },
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

        nodes = [self._normalize_node(n) for n in data.get("connected_nodes", [])]

        # Also fetch relationships for the starting node
        relationships: list[dict[str, Any]] = []
        try:
            rels_resp = await client.get(
                f"{base}/api/v1/nodes/{start_entity_type.lower()}/{start_entity_id}/relationships",
                params={"direction": direction, "limit": 500},
                headers=headers,
            )
            if rels_resp.status_code == 200:
                node_ids = {n["id"] for n in nodes}
                node_ids.add(start_entity_id)
                for r in rels_resp.json():
                    rel = self._normalize_relationship(r)
                    if rel["from_id"] in node_ids and rel["to_id"] in node_ids:
                        relationships.append(rel)
        except Exception as e:
            logger.debug(f"Could not fetch relationships for traverse: {e}")

        return {
            "nodes": nodes,
            "relationships": relationships,
            "depth": data.get("max_depth", max_depth),
        }

    async def list_entities(
        self,
        project_code: str,
        environment: str,
        token: str,
        entity_type: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List entities. Normalizes: adds id = entity_id."""
        client = await self._get_client()
        base = self._resolve_url(project_code, environment)
        resp = await client.get(
            f"{base}/api/v1/nodes/{entity_type.lower()}/",
            params={"limit": limit, "offset": offset},
            headers=self._headers(token),
        )
        resp.raise_for_status()
        return [{"id": item.get("entity_id", ""), **item} for item in resp.json()]

    async def get_entity(
        self,
        project_code: str,
        environment: str,
        token: str,
        entity_type: str,
        entity_id: str,
    ) -> dict[str, Any]:
        """Get single entity. Normalizes: adds id = entity_id."""
        client = await self._get_client()
        base = self._resolve_url(project_code, environment)
        resp = await client.get(
            f"{base}/api/v1/nodes/{entity_type.lower()}/{entity_id}",
            headers=self._headers(token),
        )
        resp.raise_for_status()
        data = resp.json()
        data["id"] = data.get("entity_id", entity_id)
        return data

    async def list_relationships(
        self,
        project_code: str,
        environment: str,
        token: str,
        relationship_type: str,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List relationships of a type. Normalizes to {id, type, from_id, to_id}."""
        client = await self._get_client()
        base = self._resolve_url(project_code, environment)
        resp = await client.get(
            f"{base}/api/v1/relationships/{relationship_type.lower()}/",
            params={"limit": limit, "offset": offset},
            headers=self._headers(token),
        )
        resp.raise_for_status()
        return [self._normalize_relationship(r) for r in resp.json()]

    # ====================================================================
    # WRITE OPERATIONS
    # ====================================================================

    async def bulk_create_entities(
        self,
        project_code: str,
        environment: str,
        token: str,
        entities: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Bulk create entities. Returns {entity_type: count}."""
        client = await self._get_client()
        base = self._resolve_url(project_code, environment)
        headers = self._headers(token)

        # Group by type
        by_type: dict[str, list[dict[str, Any]]] = {}
        for e in entities:
            by_type.setdefault(e["entity_type"], []).append(e)

        results: dict[str, int] = {}
        for entity_type, type_entities in by_type.items():
            api_type = entity_type.lower()
            created = 0

            for i in range(0, len(type_entities), MAX_BULK_SIZE):
                batch = type_entities[i : i + MAX_BULK_SIZE]
                payload = {
                    "nodes": [
                        {"entity_id": e["entity_id"], "data": e.get("properties", {})}
                        for e in batch
                    ]
                }
                resp = await client.post(
                    f"{base}/api/v1/data/bulk/nodes/{api_type}",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code not in (200, 201):
                    raise RuntimeError(
                        f"Bulk create {entity_type} failed: "
                        f"{resp.status_code} — {resp.text[:200]}"
                    )
                created += resp.json().get("created", len(batch))

            results[entity_type] = created
            logger.info(f"Created {created}/{len(type_entities)} {entity_type} entities")

        return results

    async def bulk_create_relationships(
        self,
        project_code: str,
        environment: str,
        token: str,
        relationships: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Bulk create relationships. Returns {rel_type: count}."""
        client = await self._get_client()
        base = self._resolve_url(project_code, environment)
        headers = self._headers(token)

        by_type: dict[str, list[dict[str, Any]]] = {}
        for r in relationships:
            by_type.setdefault(r["rel_type"], []).append(r)

        results: dict[str, int] = {}
        for rel_type, type_rels in by_type.items():
            api_type = rel_type.lower()
            created = 0

            for i in range(0, len(type_rels), MAX_BULK_SIZE):
                batch = type_rels[i : i + MAX_BULK_SIZE]
                payload = {
                    "relationships": [
                        {
                            "from_id": r["from_id"],
                            "to_id": r["to_id"],
                            **({"data": r["properties"]} if r.get("properties") else {}),
                        }
                        for r in batch
                    ]
                }
                resp = await client.post(
                    f"{base}/api/v1/data/bulk/relationships/{api_type}",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code not in (200, 201):
                    raise RuntimeError(
                        f"Bulk create {rel_type} failed: "
                        f"{resp.status_code} — {resp.text[:200]}"
                    )
                created += resp.json().get("created", len(batch))

            results[rel_type] = created
            logger.info(f"Created {created}/{len(type_rels)} {rel_type} relationships")

        return results

    # ====================================================================
    # NORMALIZATION HELPERS
    # ====================================================================

    @staticmethod
    def _normalize_node(node_data: dict[str, Any]) -> dict[str, Any]:
        entity_id = node_data.get("entity_id", "")
        path = node_data.get("hierarchical_path", "")
        label = path.split(":")[-1] if path else "Unknown"
        return {
            "id": entity_id,
            "labels": [label],
            "properties": {**node_data, "id": entity_id},
        }

    @staticmethod
    def _normalize_relationship(rel_data: dict[str, Any]) -> dict[str, Any]:
        rel_id = rel_data.get("rel_id", rel_data.get("id", 0))
        return {
            "id": str(rel_id),
            "type": rel_data.get("rel_type", rel_data.get("type", "")),
            "from_id": rel_data.get("from_id", ""),
            "to_id": rel_data.get("to_id", ""),
            "properties": {
                k: v
                for k, v in rel_data.items()
                if k not in ("rel_id", "from_id", "to_id", "rel_type", "from_path", "to_path")
            },
        }
