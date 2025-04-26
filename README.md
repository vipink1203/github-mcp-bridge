# MCP GITHUB ENTERPRISE 🌉
[![Python >=3.9](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)  
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-purple)](https://github.com/modelcontextprotocol/python-sdk)  
[![GitHub API](https://img.shields.io/badge/GitHub-API-black)](https://docs.github.com/en/rest)

A Model Context Protocol (MCP) server that lets AI agents (Claude, ChatGPT, etc.) query your GitHub Enterprise license data. Securely fetch license summaries, per-user details, org memberships, and enterprise roles via the `/consumed-licenses` endpoint.

---

## 📊 Capabilities & Example Prompts

- **License Summary**  
  • `"Show me our GitHub Enterprise license summary"`  
  • `"How many licenses are we currently using?"`

- **Detailed License Usage**  
  • `"List all consumed GitHub licenses"`  
  • `"Do we have any unused GitHub licenses?"`

- **User Lookup**  
  • `"What GitHub orgs does johndoe belong to?"`  
  • `"What enterprise roles does johndoe have?"`  
  • `"Is johndoe an owner in our enterprise?"`  
  • `"Get detailed info about johndoe"`  
  • `"Does johndoe have 2FA enabled?"`  

---

## 🌟 Features

- **License Analytics**: Total vs. consumed seats  
- **User Lookup**: Org memberships, roles, 2FA, SAML ID  
- **Pagination**: Handles large enterprises automatically  
- **Dual Transports**: stdio for direct MCP, SSE for HTTP  
- **Kubernetes-Ready**: Deploy on EKS/GKE or any K8s cluster  

---

## 📋 Prerequisites

- Python 3.9+  
- GitHub PAT with `read:enterprise` / license scopes  
- GitHub Enterprise Cloud tenant  

---

## 🚀 Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/vipink1203/mcp-github-enterprise.git
cd mcp-github-enterprise
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env: set GITHUB_TOKEN and GITHUB_ENTERPRISE_URL
```

### 3. Run

#### stdio transport
```bash
export TRANSPORT=stdio
python main.py
```

#### SSE transport
```bash
export TRANSPORT=sse PORT=8050
python main.py
```

## 🐳 Docker & n8n

Add this service to your docker-compose.yml alongside n8n:

```yaml
services:
  github-mcp:
    image: ghcr.io/vipink1203/mcp-github-enterprise:latest
    environment:
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_ENTERPRISE_URL=${GITHUB_ENTERPRISE_URL}
      - TRANSPORT=sse
      - PORT=8050
    ports:
      - "8050:8050"
    restart: unless-stopped
    networks:
      - n8n-network
```

In n8n's UI, enable the MCP client:
- Settings → Credentials → New Credential
- Choose MCP Client API, set URL to http://github-mcp:8050/sse

## 🔌 Client Configuration
 
 ### Claude Desktop / Windsurf / Cursor
 
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

 
 ## 📊 Example Use Cases
 
 - **Enterprise User Management**: Automate user onboarding and offboarding
 - **License Monitoring**: Get alerts when licenses are close to expiration
 - **Organization Analysis**: Analyze organization structures and relationships
 - **User Access Auditing**: Track user permissions and access levels
 - **AI-powered GitHub Insights**: Let AI analyze your enterprise GitHub data


## 🔌 MCP Tools & Resources

### Tools

| Name | Description |
|------|-------------|
| `list_consumed_licenses` | Summarize licenses, optionally include users |
| `get_user_organizations` | List a user's GitHub org memberships |
| `get_user_enterprise_roles` | List a user's enterprise roles |
| `get_user_detail` | Full license detail for a user |

### Resources

| URI | Description |
|-----|-------------|
| `github://consumed-licenses/{dummy}` | Full license usage + user details |
| `github://user/{username}/roles` | Org & enterprise roles for a user |


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

Built with ❤️ for seamless AI ↔️ GitHub Enterprise integration.
