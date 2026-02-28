# Graforest MCP Server

**Build knowledge graphs with AI.** 13 tools for creating, populating, searching, and exploring knowledge graphs through the Model Context Protocol.

[![License](https://img.shields.io/badge/license-Proprietary-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/graforest-mcp.svg)](https://pypi.org/project/graforest-mcp/)

## What Is This?

Graforest MCP lets AI agents (Claude, Cursor, VS Code, etc.) build and query knowledge graphs. No database setup. No Neo4j config. Just tell your AI agent what you want to know.

```
"Create a knowledge graph about organic chemistry and populate it from my notes"
→ 2 minutes later: Searchable knowledge graph with entities and relationships
```

The AI agent handles intelligence (entity extraction, reasoning). Graforest handles data (storage, search, traversal).

## Installation

```bash
pip install graforest-mcp
```

## Quick Start

### 1. Get Your API Key

Visit [graforest.ai/settings](https://graforest.ai/settings) and create an API key (`gf_sk_...`).

### 2. Configure Your AI Agent

**VS Code** — Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "graforest": {
      "command": "uvx",
      "args": ["graforest-mcp"],
      "env": {
        "GRAFOREST_API_KEY": "gf_sk_your_key_here"
      }
    }
  }
}
```

**Cursor** — Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "graforest": {
      "command": "uvx",
      "args": ["graforest-mcp"],
      "env": {
        "GRAFOREST_API_KEY": "gf_sk_your_key_here"
      }
    }
  }
}
```

**Claude Desktop** — Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "graforest": {
      "command": "uvx",
      "args": ["graforest-mcp"],
      "env": {
        "GRAFOREST_API_KEY": "gf_sk_your_key_here"
      }
    }
  }
}
```

**Smithery:**

```bash
npx @smithery/cli install @graforest/mcp
```

---

## 13 Tools

### Provisioning (3 tools)

| Tool | Description |
|------|-------------|
| `create_knowledge_project` | Provision a new knowledge graph (Neo4j) |
| `list_knowledge_projects` | List all graph projects |
| `delete_knowledge_project` | Delete a graph project permanently |

### Data Write (2 tools)

| Tool | Description |
|------|-------------|
| `add_knowledge_nodes` | Bulk create entities (max 500/batch) |
| `add_knowledge_relationships` | Bulk create relationships (max 500/batch) |

### Data Read (6 tools)

| Tool | Description |
|------|-------------|
| `search_knowledge_graph` | Full-text search across all node fields |
| `get_knowledge_schema` | Get entity types, relationship types, and fields |
| `get_knowledge_statistics` | Node and relationship counts by type |
| `traverse_knowledge_graph` | Walk connections from any node |
| `list_knowledge_entities` | List entities by type (paginated) |
| `get_knowledge_entity` | Get a single entity by ID |

### Ingestion (1 tool)

| Tool | Description |
|------|-------------|
| `ingest_text_content` | Prepare text for the 3-call extraction workflow |

### Utility (1 tool)

| Tool | Description |
|------|-------------|
| `fetch_url_content` | Scrape a URL and return clean text |

---

## 3-Call Ingestion Workflow

The recommended way to populate a knowledge graph from text:

1. **`ingest_text_content(project_code, text)`** → Returns the graph schema + extraction instructions
2. **LLM extracts** all entities and relationships from the text (guided by the instructions)
3. **`add_knowledge_nodes`** + **`add_knowledge_relationships`** → Bulk write everything

The AI does the thinking. Graforest stores the results.

---

## Architecture

```
AI Agent → graforest-mcp → Graph APIs (Neo4j databases)
                         → RationalBloks API (infrastructure provisioning)
```

- **No AI inside the MCP server** — the LLM is the intelligence, Graforest is the data layer
- **Dual transport**: STDIO (local IDEs) + HTTP/SSE (cloud deployment)
- **API key auth**: `gf_sk_` prefix for all Graforest keys

---

## Resources & Prompts

**Resources:**
- `graforest://docs/getting-started` — Quick start guide
- `graforest://docs/knowledge-graph` — Knowledge graph concepts

**Prompts:**
- `ingest-content` — Guided content ingestion workflow
- `explore-graph` — Guided graph exploration workflow

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GRAFOREST_API_KEY` | Yes (STDIO) | — | Your Graforest API key |
| `TRANSPORT` | No | `stdio` | Transport mode: `stdio` or `http` |
| `PORT` | No | `8000` | HTTP server port |
| `HOST` | No | `0.0.0.0` | HTTP server bind address |

---

## Support

- **Website:** [graforest.ai](https://graforest.ai)
- **Documentation:** [graforest.ai/docs](https://graforest.ai/docs)
- **Email:** support@graforest.ai
