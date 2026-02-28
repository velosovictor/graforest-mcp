# ============================================================================
# GRAFOREST MCP SERVER DOCKERFILE
# ============================================================================
# MCP Server for AI Agents — HTTP/SSE transport for cloud deployment.
# Deployed as a LogicBlok module via the RationalBloks platform pipeline.
#
# Requirements (LogicBlok module contract):
#   - Port 8000
#   - /health endpoint
#   - Non-root user (UID 1000)
# ============================================================================

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base

LABEL maintainer="Graforest Platform"
LABEL description="graforest-mcp — Knowledge Graph MCP Server (HTTP/SSE transport)"
LABEL version="0.1.0"

# Security: non-root user with UID/GID 1000 (LogicBlok standard)
RUN groupadd -r -g 1000 mcpuser && useradd -r -u 1000 -g mcpuser mcpuser

# Minimal system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ============================================================================
# DEPENDENCY STAGE
# ============================================================================
FROM base AS dependencies

WORKDIR /app
COPY pyproject.toml uv.lock ./

ENV UV_HTTP_TIMEOUT=120
RUN uv sync --no-dev --no-install-project

# ============================================================================
# PRODUCTION STAGE
# ============================================================================
FROM dependencies AS production

WORKDIR /app
COPY --chown=mcpuser:mcpuser . .

# Install the project (uses existing dependency cache)
RUN uv sync --no-dev

# Permissions
RUN chown -R mcpuser:mcpuser /app
RUN mkdir -p /home/mcpuser/.cache/uv && \
    chown -R mcpuser:mcpuser /home/mcpuser/.cache

USER mcpuser

# Health check (LogicBlok contract: /health on port 8000)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TRANSPORT=http
ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["uv", "run", "graforest-mcp"]
