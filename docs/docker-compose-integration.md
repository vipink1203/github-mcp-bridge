# Integrating GitHub MCP Bridge with Existing Docker Compose Setups

This guide explains how to integrate the GitHub MCP Bridge with your existing Docker Compose configuration, especially if you have n8n already running in a containerized environment.

## Option 1: Using the Provided docker-compose.yml

If you don't already have a Docker Compose setup, you can use the provided `docker-compose.yml` file as a starting point:

1. Create a `.env` file with your GitHub token:

```bash
echo "GITHUB_TOKEN=your_github_token" > .env
```

2. Start the services:

```bash
docker-compose up -d
```

## Option 2: Integrating with an Existing n8n Setup

If you already have n8n running with Docker Compose, there are several ways to integrate the GitHub MCP Bridge:

### Method A: Add to Existing docker-compose.yml

Add the GitHub MCP service directly to your existing `docker-compose.yml` file:

```yaml
# Add this to your existing docker-compose.yml
services:
  # ... your existing services
  
  github-mcp:
    build:
      context: ./github-mcp-bridge  # Path to the cloned repository
      dockerfile: Dockerfile
    container_name: github-mcp-bridge
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_ENTERPRISE_URL=${GITHUB_ENTERPRISE_URL:-https://api.github.com}
      - TRANSPORT=sse
      - PORT=8050
      - HOST=0.0.0.0
    ports:
      - "8050:8050"
    restart: unless-stopped
    networks:
      - n8n-network  # Use your existing network
```

### Method B: Using docker-compose.override.yml

Another elegant approach is to use a Docker Compose override file, which doesn't require modifying your original setup:

1. Create a `docker-compose.override.yml` file in the same directory as your existing `docker-compose.yml`:

```yaml
# docker-compose.override.yml
version: '3'

services:
  github-mcp:
    build:
      context: ./github-mcp-bridge  # Path to the cloned repository
      dockerfile: Dockerfile
    container_name: github-mcp-bridge
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_ENTERPRISE_URL=${GITHUB_ENTERPRISE_URL:-https://api.github.com}
      - TRANSPORT=sse
      - PORT=8050
      - HOST=0.0.0.0
    ports:
      - "8050:8050"
    restart: unless-stopped
    networks:
      - default  # This will use the default network from the main compose file
```

2. Update your `.env` file to include the GitHub token:

```bash
# Add this to your existing .env file
GITHUB_TOKEN=your_github_token
```

3. Run your regular Docker Compose commands, and the override will be automatically applied:

```bash
docker-compose up -d
```

## Configuring n8n to Use the GitHub MCP Bridge

Once your GitHub MCP Bridge is running in the same Docker network as n8n, you can configure n8n to use it:

1. Install the MCP community node in n8n (if not already installed):

```yaml
# Add these environment variables to your n8n service
environment:
  - N8N_COMMUNITY_PACKAGES=n8n-nodes-mcp
  - N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true
```

2. In the n8n web interface, add a new MCP credential:
   - Go to **Settings** > **Credentials** > **New Credentials**
   - Select **MCP Client API**
   - Configure with:
     - **Name**: GitHub MCP
     - **Transport Type**: Server-Sent Events (SSE)
     - **Server URL**: `http://github-mcp:8050/sse`
     
     Note: Use the service name (`github-mcp`) instead of localhost since they're in the same Docker network

3. Test the connection by creating a workflow with the MCP Client node.

## Network Troubleshooting

If you have issues connecting from n8n to the GitHub MCP service:

1. Check that both services are on the same network:

```bash
docker network inspect n8n-network
```

2. Verify the GitHub MCP service is running properly:

```bash
docker logs github-mcp-bridge
```

3. If needed, try connecting directly from the n8n container:

```bash
docker exec -it n8n curl http://github-mcp:8050/health
```

## Example: Complete n8n + GitHub MCP Bridge Setup

Here's a full example of a `docker-compose.yml` with both n8n and GitHub MCP Bridge:

```yaml
version: '3'

services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_COMMUNITY_PACKAGES=n8n-nodes-mcp
      - N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true
      - MCP_GITHUB_URL=http://github-mcp:8050
    volumes:
      - ~/.n8n:/home/node/.n8n
    networks:
      - n8n-network

  github-mcp:
    build:
      context: ./github-mcp-bridge
      dockerfile: Dockerfile
    container_name: github-mcp-bridge
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_ENTERPRISE_URL=${GITHUB_ENTERPRISE_URL:-https://api.github.com}
      - TRANSPORT=sse
      - PORT=8050
      - HOST=0.0.0.0
    ports:
      - "8050:8050"
    restart: unless-stopped
    networks:
      - n8n-network

networks:
  n8n-network:
    driver: bridge
```

Save this file and start both services with:

```bash
docker-compose up -d
```

## Advanced: Creating a Multi-MCP Server Setup

If you want to run multiple MCP servers alongside n8n, you can extend your Docker Compose file to include all of them:

```yaml
version: '3'

services:
  n8n:
    # ... n8n configuration

  github-mcp:
    # ... GitHub MCP configuration
    
  weather-mcp:
    image: example/weather-mcp:latest
    environment:
      - WEATHER_API_KEY=${WEATHER_API_KEY}
      - TRANSPORT=sse
      - PORT=8051
    ports:
      - "8051:8051"
    networks:
      - n8n-network
      
  database-mcp:
    image: example/database-mcp:latest
    environment:
      - DB_CONNECTION_STRING=${DB_CONNECTION_STRING}
      - TRANSPORT=sse
      - PORT=8052
    ports:
      - "8052:8052"
    networks:
      - n8n-network

networks:
  n8n-network:
    driver: bridge
```

This way, n8n can connect to multiple specialized MCP servers, each providing different functionality.
