FROM python:3.11-slim

LABEL maintainer="vipink1203@gmail.com"

WORKDIR /app

# Install and pin dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy *all* your code (not just main.py) so imports will work
COPY . .

# Expose the SSE port by default (for transport=sse)
EXPOSE 8050

# Default to SSE mode in containers — override at runtime if you really want stdio
ENV PYTHONUNBUFFERED=1 \
    TRANSPORT=sse \
    PORT=8050 \
    HOST=0.0.0.0

# Optional healthcheck for Kubernetes or Docker Compose
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Run the MCP server
CMD ["python", "main.py"]
