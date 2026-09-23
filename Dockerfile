# Glama MCP Server Dockerfile for jev-harness
FROM python:3.12-slim

WORKDIR /app

# Copy project manifest and source
COPY pyproject.toml .
COPY src/ ./src/

# Install package (pure Python standard library, zero external runtime dependencies)
RUN pip install --no-cache-dir .

# Force unbuffered I/O for clean JSON-RPC stdio protocol communication
ENV PYTHONUNBUFFERED=1

# Expose jev-mcp entrypoint for MCP clients and Glama introspection
ENTRYPOINT ["jev-mcp"]
