# Graforest MCP

Knowledge graph tools for AI agents. Store, search, and explore knowledge graphs through the Model Context Protocol.

## Quick Start

```bash
# Install
pip install graforest-mcp

# Or run directly with uvx
uvx graforest-mcp
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GRAFOREST_API_KEY` | Yes | Your Graforest API key (`gf_sk_...`) |
| `TRANSPORT` | No | `stdio` (default) or `http` |
| `PORT` | No | HTTP port (default: 8000) |
| `HOST` | No | HTTP host (default: 0.0.0.0) |

### Claude Desktop

Add to `claude_desktop_config.json`:

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

### Cursor

Add to `.cursor/mcp.json`:

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

### VS Code

Add to `.vscode/mcp.json`:

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

### Smithery

```bash
npx @smithery/cli install @graforest/mcp
```

## Tools (13)

### Provisioning (3)
| Tool | Description |
|------|-------------|
| `create_knowledge_project` | Provision a new knowledge graph |
| `list_knowledge_projects` | List all graph projects |
| `delete_knowledge_project` | Delete a graph project |

### Data Write (2)
| Tool | Description |
|------|-------------|
| `add_knowledge_nodes` | Bulk create entities |
| `add_knowledge_relationships` | Bulk create relationships |

### Data Read (6)
| Tool | Description |
|------|-------------|
| `search_knowledge_graph` | Full-text search across nodes |
| `get_knowledge_schema` | Get entity/relationship types |
| `get_knowledge_statistics` | Node/relationship counts |
| `traverse_knowledge_graph` | Walk connections from a node |
| `list_knowledge_entities` | List entities by type |
| `get_knowledge_entity` | Get a single entity |

### Ingestion (1)
| Tool | Description |
|------|-------------|
| `ingest_text_content` | Prepare text for 3-call extraction workflow |

### Utility (1)
| Tool | Description |
|------|-------------|
| `fetch_url_content` | Scrape URL for clean text |

## 3-Call Ingestion Workflow

The recommended way to populate a knowledge graph:

1. **`ingest_text_content(project_code, text)`** → Returns schema + extraction instructions
2. **LLM extracts** ALL entities and relationships from the text
3. **`add_knowledge_nodes(project_code, entities)`** → Bulk create all nodes
4. **`add_knowledge_relationships(project_code, relationships)`** → Bulk create all edges

## Architecture

```
AI Agent → graforest-mcp → Graph APIs (Neo4j)
                         → RationalBloks API (infrastructure provisioning)
```

- **NO AI inside** — the LLM is the intelligence, Graforest is the data layer
- Dual transport: STDIO (local) + HTTP (cloud deployment)
- API key authentication (`gf_sk_` prefix)

## Resources

- **Getting Started Guide**: `graforest://docs/getting-started`
- **Knowledge Graph Guide**: `graforest://docs/knowledge-graph`

## Prompts

- **`ingest-content`**: Guided content ingestion workflow
- **`explore-graph`**: Guided graph exploration workflow

## License

Proprietary — see [LICENSE](LICENSE) for details.

## Links

- Website: [graforest.ai](https://graforest.ai)
- Documentation: [graforest.ai/docs](https://graforest.ai/docs)
- GitHub: [github.com/velosovictor/graforest-mcp](https://github.com/velosovictor/graforest-mcp)
