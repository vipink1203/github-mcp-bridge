# GitHub MCP Bridge 🌉

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-purple)](https://github.com/modelcontextprotocol/python-sdk)
[![GitHub API](https://img.shields.io/badge/GitHub-API-black)](https://docs.github.com/en/rest)

A powerful Model Context Protocol (MCP) server that enables AI agents (like Claude, ChatGPT, and others) to securely access and interact with GitHub Enterprise data. This project provides a bridge between AI systems and GitHub's Enterprise features, allowing for access to enterprise users, organizations, emails, and license information.

![GitHub MCP Bridge Diagram](https://raw.githubusercontent.com/vipink1203/github-mcp-bridge/main/docs/images/diagram.png)

## 🌟 Features

- **User Management**: List all enterprise users and get detailed information
- **Organization Access**: View all organizations and their details
- **Email Retrieval**: Access user email information (requires admin privileges)
- **License Management**: View and manage enterprise licenses, including consumed licenses
- **Dual Transport Support**: Use stdio for direct integration or SSE for service deployment
- **Kubernetes Ready**: Deploy in EKS, GKE, or any Kubernetes environment
- **n8n Integration**: Create workflows with GitHub Enterprise data

## 📋 Prerequisites

- Python 3.9+
- GitHub Personal Access Token with appropriate scopes
- GitHub Enterprise instance (optional, can use github.com API)

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
export GITHUB_ENTERPRISE_NAME=your_enterprise_name
export TRANSPORT=stdio
python main.py
```

For SSE transport (standalone service):
```bash
export GITHUB_TOKEN=your_github_token
export GITHUB_ENTERPRISE_NAME=your_enterprise_name
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
      - GITHUB_ENTERPRISE_URL=${GITHUB_ENTERPRISE_URL:-https://api.github.com}
      - GITHUB_ENTERPRISE_NAME=${GITHUB_ENTERPRISE_NAME}
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
GITHUB_ENTERPRISE_NAME=your_enterprise_name
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
      - GITHUB_ENTERPRISE_NAME=${GITHUB_ENTERPRISE_NAME}
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
GITHUB_ENTERPRISE_NAME=your_enterprise_name
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
      - GITHUB_ENTERPRISE_URL=${GITHUB_ENTERPRISE_URL:-https://api.github.com}
      - GITHUB_ENTERPRISE_NAME=${GITHUB_ENTERPRISE_NAME}
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
| `list_enterprise_users` | Get all users in the GitHub Enterprise instance |
| `get_user_info` | Get detailed information for a specific user |
| `list_user_organizations` | Get all organizations a user belongs to |
| `list_enterprise_organizations` | Get all organizations in the enterprise |
| `get_user_emails` | Get email addresses for a user |
| `list_enterprise_licenses` | Get all licenses in the GitHub Enterprise instance |
| `get_license_info` | Get detailed information for a specific license |
| `list_consumed_licenses` | Get all consumed licenses with detailed user information |

### Available Resources

| Resource | Description |
|----------|-------------|
| `github://users/{dummy}` | List of all GitHub Enterprise users |
| `github://organizations/{dummy}` | List of all GitHub Enterprise organizations |
| `github://user/{username}` | Information about a specific user |
| `github://user/{username}/organizations` | Organizations for a specific user |
| `github://licenses/{dummy}` | List of all GitHub Enterprise licenses |
| `github://consumed-licenses/{dummy}` | List of all consumed licenses with user details |

## 🔌 Client Configuration

### Claude Desktop / Windsurf

#### Setting up Claude Desktop Configuration

The Claude Desktop settings file is located at:
- On macOS: `~/Library/Application Support/Claude Desktop/settings.json`
- On Windows: `%APPDATA%\Claude Desktop\settings.json` 
- On Linux: `~/.config/Claude Desktop/settings.json`

You can use any name for your MCP server (not just "github"). Here's an example using "github-ent" as the server name:

```json
{
  "mcpServers": {
    "github-ent": {
      "command": "/path/to/your/venv/python",
      "args": ["/path/to/github-mcp-bridge/main.py"],
      "env": {
        "GITHUB_TOKEN": "your_github_token",
        "GITHUB_ENTERPRISE_NAME": "your_enterprise_name",
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
- `your_enterprise_name` with your GitHub Enterprise name

After editing the settings file, restart Claude Desktop for the changes to take effect.

#### Testing the Integration

You can test the integration by asking Claude:
"Can you list the GitHub Enterprise users using the github-ent MCP tool?"

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
export GITHUB_ENTERPRISE_NAME=your_enterprise_name
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
        - name: GITHUB_ENTERPRISE_NAME
          valueFrom:
            secretKeyRef:
              name: github-mcp-secrets
              key: enterprise-name
        - name: TRANSPORT
          value: "sse"
        ports:
        - containerPort: 8050
```

For a complete EKS deployment guide, see the [wiki](https://github.com/vipink1203/github-mcp-bridge/wiki/EKS-Deployment-Guide).

## 📊 Example Use Cases

- **Enterprise User Management**: Automate user onboarding and offboarding
- **License Monitoring**: Get alerts when licenses are close to expiration
- **License Consumption Analysis**: Track which users are consuming licenses across different organizations
- **Organization Analysis**: Analyze organization structures and relationships
- **User Access Auditing**: Track user permissions and access levels
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
