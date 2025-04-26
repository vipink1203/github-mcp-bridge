# GitHub MCP Bridge 🌉

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-purple)](https://github.com/modelcontextprotocol/python-sdk)
[![GitHub API](https://img.shields.io/badge/GitHub-API-black)](https://docs.github.com/en/rest)

A powerful Model Context Protocol (MCP) server that enables AI agents (like Claude, ChatGPT, and others) to securely access and interact with GitHub Enterprise data. This bridge provides deep insights into your enterprise's license usage and user information.

## 📊 Capabilities & Example Prompts

### License Management and Usage Insights
- **"Show me our GitHub Enterprise license summary"** - Get total seats purchased and consumed
- **"How many GitHub licenses are we currently using?"** - Quick overview of license usage
- **"List all our consumed GitHub licenses"** - Detailed breakdown of all used licenses
- **"Do we have any unused GitHub licenses?"** - Check for available licenses

### User Information and Organization Access
- **"What GitHub organizations is username@example.com part of?"** - Find user's organizations
- **"What enterprise roles does username have?"** - Check for admin privileges
- **"Is username an owner of any GitHub organizations?"** - Verify ownership status
- **"Get detailed information about username"** - Complete user profile

### Enterprise Administration
- **"Which users have owner access to our GitHub Enterprise?"** - Find privileged users
- **"Show me all users with SAML identities in GitHub"** - Check SSO integration
- **"List all users with 2FA enabled in GitHub"** - Security compliance check
- **"How many Visual Studio subscribers have GitHub licenses?"** - Cross-product license usage

### Best Practices for Effective Queries
- Be specific with usernames when asking about individual users
- Use "include_users" flag to see detailed user information in license reports
- For large enterprises, set "full_pagination" to true for complete data

![GitHub MCP Bridge Diagram](https://raw.githubusercontent.com/vipink1203/github-mcp-bridge/main/images/diagram.png)

## 🌟 Features

- **License Analytics**: Get comprehensive insights into your GitHub Enterprise license usage
- **User Management**: Analyze detailed user information including organization access
- **Role Inspection**: Check user permissions across both organizations and enterprise
- **Deep Integration**: Extracts rich data from the consumed-licenses endpoint
- **Full Pagination**: Automatically handles large datasets with multiple pages
- **Dual Transport Support**: Use stdio for direct integration or SSE for service deployment
- **Kubernetes Ready**: Deploy in EKS, GKE, or any Kubernetes environment

## 📋 Prerequisites

- Python 3.9+
- GitHub Personal Access Token with appropriate scopes
- GitHub Enterprise Cloud (required for license consumption data)

## 🚀 Quick Start

### Installation

1. Clone this repository:
```bash
git clone https://github.com/vipink1203/github-mcp-bridge.git
cd github-mcp-bridge
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env file with your GitHub token, enterprise name, and other settings
```

### Running the Server

#### Using the setup script:
```bash
chmod +x setup.sh
./setup.sh
```

#### Manual startup:

For stdio transport (direct integration with MCP clients):
```bash
export GITHUB_TOKEN=your_github_token
export GITHUB_ENTERPRISE_URL=https://api.github.com/enterprises/your-enterprise-name
export TRANSPORT=stdio
python main.py
```

For SSE transport (standalone service):
```bash
export GITHUB_TOKEN=your_github_token
export GITHUB_ENTERPRISE_URL=https://api.github.com/enterprises/your-enterprise-name
export TRANSPORT=sse
export PORT=8050
python main.py
```

## 🐳 Running with Docker and n8n

The most common use case for this MCP server is to run it alongside n8n in a containerized environment.

### Option 1: Adding to Existing n8n Docker Compose Setup

If you already have n8n running with Docker Compose, add these lines to your existing `docker-compose.yml` file:

```yaml
services:
  # ... your existing n8n service and other services
  
  github-mcp:
    image: ghcr.io/vipink1203/github-mcp-bridge:latest
    # Or build from local source:
    # build:
    #   context: ./github-mcp-bridge
    #   dockerfile: Dockerfile
    container_name: github-mcp-bridge
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_ENTERPRISE_URL=${GITHUB_ENTERPRISE_URL}
      - TRANSPORT=sse
      - PORT=8050
      - HOST=0.0.0.0
    ports:
      - "8050:8050"
    restart: unless-stopped
    networks:
      - n8n-network  # Use your existing n8n network
```

Make sure to add your GitHub token to your `.env` file:
```
GITHUB_TOKEN=your_github_token_here
GITHUB_ENTERPRISE_URL=https://api.github.com/enterprises/your-enterprise-name
```

### Option 2: Using docker-compose.override.yml

If you don't want to modify your original n8n docker-compose.yml:

1. Create a `docker-compose.override.yml` in the same directory as your existing n8n `docker-compose.yml`:

```yaml
version: '3'

services:
  # Add MCP settings to n8n
  n8n:
    environment:
      - N8N_COMMUNITY_PACKAGES=n8n-nodes-mcp
      - N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true
      
  # Add GitHub MCP service
  github-mcp:
    image: ghcr.io/vipink1203/github-mcp-bridge:latest
    container_name: github-mcp-bridge
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_ENTERPRISE_URL=${GITHUB_ENTERPRISE_URL}
      - TRANSPORT=sse
      - PORT=8050
    ports:
      - "8050:8050"
    restart: unless-stopped
    # This will use the same network as your n8n service
```

2. Update your `.env` file to include the GitHub token:
```
GITHUB_TOKEN=your_github_token_here
GITHUB_ENTERPRISE_URL=https://api.github.com/enterprises/your-enterprise-name
```

3. Run your Docker Compose as usual:
```bash
docker-compose up -d
```

### Option 3: Starting from Scratch

If you don't have n8n set up yet, here's a complete docker-compose.yml with both n8n and GitHub MCP:

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
    volumes:
      - ~/.n8n:/home/node/.n8n
    networks:
      - n8n-network

  github-mcp:
    image: ghcr.io/vipink1203/github-mcp-bridge:latest
    container_name: github-mcp-bridge
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_ENTERPRISE_URL=${GITHUB_ENTERPRISE_URL}
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

### Configuring n8n to Use the GitHub MCP

1. Make sure the n8n-nodes-mcp package is enabled in your n8n environment:
```yaml
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
     
     Note: Use the container name (`github-mcp`) instead of localhost since they're in the same Docker network

### Troubleshooting

If you have issues connecting from n8n to the GitHub MCP service:

1. **Network Connectivity**: Ensure both containers are on the same network:
```bash
docker network inspect n8n-network
```

2. **DNS Resolution**: Verify n8n can resolve the GitHub MCP service by name:
```bash
docker exec -it n8n ping github-mcp
```

3. **Check Logs**: Look for errors in the GitHub MCP container:
```bash
docker logs github-mcp-bridge
```

4. **Port Access**: Verify the service is listening on the correct port:
```bash
docker exec -it n8n curl http://github-mcp:8050/health
```

5. **Environment Variables**: Make sure all required variables are set correctly.

## 🛠️ MCP Tools & Resources

### Available Tools

| Tool | Description |
|------|-------------|
| `list_consumed_licenses` | Get a summary of license usage with optional user details |
| `get_user_organizations` | Get all organizations a specific user belongs to |
| `get_user_enterprise_roles` | Get enterprise roles for a specific user |
| `get_user_detail` | Get detailed information for a specific user |

### Available Resources

| Resource | Description |
|----------|-------------|
| `github://consumed-licenses/{dummy}` | Complete license usage data with all user details |
| `github://user/{username}/roles` | Organization and enterprise roles for a specific user |

### Tool Parameters

| Tool | Parameters |
|------|------------|
| `list_consumed_licenses` | `include_users`: Include detailed user information (default: False)<br>`full_pagination`: Retrieve all pages (default: True) |
| `get_user_organizations` | `username`: GitHub username to look up<br>`full_pagination`: Retrieve all pages (default: True) |
| `get_user_enterprise_roles` | `username`: GitHub username to look up<br>`full_pagination`: Retrieve all pages (default: True) |
| `get_user_detail` | `username`: GitHub username to look up<br>`full_pagination`: Retrieve all pages (default: True) |

## 🔌 Client Configuration

### Claude Desktop / Windsurf

#### Setting up Claude Desktop Configuration

The Claude Desktop settings file is located at:
- On macOS: `~/Library/Application Support/Claude Desktop/settings.json`
- On Windows: `%APPDATA%\Claude Desktop\settings.json` 
- On Linux: `~/.config/Claude Desktop/settings.json`

You can use any name for your MCP server. Here's an example using "github-ent" as the server name:

```json
{
  "mcpServers": {
    "github-ent": {
      "command": "/path/to/your/venv/python",
      "args": ["/path/to/github-mcp-bridge/main.py"],
      "env": {
        "GITHUB_TOKEN": "your_github_token",
        "GITHUB_ENTERPRISE_URL": "https://api.github.com/enterprises/your-enterprise-name",
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

Make sure to replace:
- `/path/to/your/venv/python` with the full path to the Python executable in your virtual environment
- `/path/to/github-mcp-bridge/main.py` with the full path to the main.py file
- `your_github_token` with your GitHub Personal Access Token
- `your-enterprise-name` with your GitHub Enterprise name

After editing the settings file, restart Claude Desktop for the changes to take effect.

#### Testing the Integration

You can test the integration by asking Claude:
"Can you list our GitHub Enterprise license usage using the github-ent MCP tool?"

### SSE Configuration

If you prefer to run the MCP server as a standalone service, you can configure Claude Desktop to use the SSE transport:

```json
{
  "mcpServers": {
    "github-ent": {
      "transport": "sse",
      "url": "http://localhost:8050/sse"
    }
  }
}
```

In this case, you'll need to start the server separately before using it with Claude Desktop:

```bash
export GITHUB_TOKEN=your_github_token
export GITHUB_ENTERPRISE_URL=https://api.github.com/enterprises/your-enterprise-name
export TRANSPORT=sse
export PORT=8050
python main.py
```

## 🌐 Enterprise Deployment

### Kubernetes / EKS

For more advanced EKS deployment options:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: github-mcp
  namespace: n8n
spec:
  replicas: 1
  selector:
    matchLabels:
      app: github-mcp
  template:
    metadata:
      labels:
        app: github-mcp
    spec:
      containers:
      - name: github-mcp
        image: ghcr.io/vipink1203/github-mcp-bridge:latest
        env:
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: github-mcp-secrets
              key: github-token
        - name: GITHUB_ENTERPRISE_URL
          valueFrom:
            secretKeyRef:
              name: github-mcp-secrets
              key: enterprise-url
        - name: TRANSPORT
          value: "sse"
        ports:
        - containerPort: 8050
```

For a complete EKS deployment guide, see the [wiki](https://github.com/vipink1203/github-mcp-bridge/wiki/EKS-Deployment-Guide).

## 📊 Example Use Cases

- **License Optimization**: Identify unused licenses to reduce costs
- **Security Compliance**: Check which users have 2FA enabled
- **Organization Auditing**: Review owner access across the enterprise
- **User Management**: Find which organizations users belong to
- **License Planning**: Track license consumption for budget planning
- **AI-powered GitHub Insights**: Let AI analyze your enterprise GitHub data

## 🔒 Security Considerations

- Store your GitHub token securely
- Use appropriate scopes for your GitHub token
- For production, consider using AWS Secrets Manager or similar
- Implement network policies in Kubernetes deployments

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- [Model Context Protocol](https://github.com/modelcontextprotocol/python-sdk) for the Python SDK
- [MCP-Mem0](https://github.com/coleam00/mcp-mem0) for providing a great template structure
- [GitHub API](https://docs.github.com/en/rest) for the comprehensive API

---

<p align="center">Built with ❤️ for AI and GitHub integration</p>
