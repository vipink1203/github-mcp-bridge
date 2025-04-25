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
- **License Management**: View and manage enterprise licenses
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
# Edit .env file with your GitHub token and other settings
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
export TRANSPORT=stdio
python main.py
```

For SSE transport (standalone service):
```bash
export GITHUB_TOKEN=your_github_token
export TRANSPORT=sse
export PORT=8050
python main.py
```

### Docker Support

Build and run with Docker:
```bash
docker build -t github-mcp-bridge .

# Run with stdio transport
docker run -i --rm -e GITHUB_TOKEN=your_token github-mcp-bridge

# Run with SSE transport
docker run -i --rm -p 8050:8050 -e TRANSPORT=sse -e GITHUB_TOKEN=your_token github-mcp-bridge
```

## 🛠️ MCP Tools & Resources

### Available Tools

| Tool | Description |
|------|-------------|
| `list_enterprise_users` | Get all users in the GitHub Enterprise instance |
| `get_user_info` | Get detailed information for a specific user |
| `list_user_organizations` | Get all organizations a user belongs to |
| `list_enterprise_organizations` | Get all organizations in the enterprise |
| `get_user_emails` | Get email addresses for a user |
| `list_enterprise_licenses` | Get all licenses in the enterprise |
| `get_license_info` | Get detailed information for a specific license |

### Available Resources

| Resource | Description |
|----------|-------------|
| `github://users` | List of all GitHub Enterprise users |
| `github://organizations` | List of all GitHub Enterprise organizations |
| `github://user/{username}` | Information about a specific user |
| `github://user/{username}/organizations` | Organizations for a specific user |
| `github://licenses` | List of all GitHub Enterprise licenses |

## 🔌 Client Configuration

### Claude Desktop / Windsurf

Add this configuration to your Claude Desktop settings:

```json
{
  "mcpServers": {
    "github": {
      "command": "/path/to/your/venv/python",
      "args": ["/path/to/main.py"],
      "env": {
        "GITHUB_TOKEN": "your_github_token",
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

### SSE Configuration

```json
{
  "mcpServers": {
    "github": {
      "transport": "sse",
      "url": "http://localhost:8050/sse"
    }
  }
}
```

## 🌐 Enterprise Deployment

### Kubernetes / EKS

For detailed enterprise deployment instructions, see our [EKS Deployment Guide](docs/eks-deployment-guide.md).

### n8n Integration

For integration with n8n workflows, refer to the [n8n Integration Guide](docs/n8n-integration-guide.md).

## 📊 Example Use Cases

- **Enterprise User Management**: Automate user onboarding and offboarding
- **License Monitoring**: Get alerts when licenses are close to expiration
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
