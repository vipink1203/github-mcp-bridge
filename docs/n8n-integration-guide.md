# Integrating GitHub MCP with n8n Workflows

This guide explains how to use the GitHub MCP server with n8n to create workflows that leverage GitHub Enterprise data.

## Prerequisites

- n8n installed and running
- The n8n-nodes-mcp community node installed
- GitHub MCP server running with SSE transport

## Step 1: Install the MCP Community Node

You need to install the n8n-nodes-mcp community node to enable MCP support in n8n.

### Option 1: Using n8n UI

1. Go to **Settings** > **Community Nodes**
2. Search for "n8n-nodes-mcp"
3. Click **Install**

### Option 2: Using Docker

If you're running n8n in Docker, add the following environment variables to your Docker configuration:

```yaml
environment:
  - N8N_COMMUNITY_PACKAGES=n8n-nodes-mcp
  - N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true
```

## Step 2: Configure the GitHub MCP Server Connection

1. In n8n, go to **Credentials** > **New Credentials**
2. Select **MCP Client API**
3. Configure the connection:
   - **Name**: GitHub Enterprise MCP
   - **Transport Type**: Server-Sent Events (SSE)
   - **Server URL**: http://github-mcp:8050/sse (adjust host/port as needed)

4. Click **Save** to store the credentials

## Step 3: Create a Workflow Using the GitHub MCP

Now you can create workflows that interact with GitHub Enterprise through the MCP server.

### Example Workflow: List Enterprise Users

1. Create a new workflow
2. Add a **Manual Trigger** node
3. Add an **MCP Client** node
   - Select the GitHub Enterprise MCP credentials
   - In **Server Action**, select **Execute Tool**
   - For **Tool Name**, select `list_enterprise_users`
   - Leave **Tool Parameters** empty
4. Add a **Set** node to process the results

### Example Workflow: Get User Information

1. Create a new workflow
2. Add a **Manual Trigger** node with an input field for username
3. Add an **MCP Client** node
   - Select the GitHub Enterprise MCP credentials
   - In **Server Action**, select **Execute Tool**
   - For **Tool Name**, select `get_user_info`
   - For **Tool Parameters**, enter JSON: `{"username": "{{$json.username}}"}`
4. Add nodes to process or display the user information

## Example n8n Workflow: GitHub Enterprise User Report

This workflow creates a report of all enterprise users and their organizations.

```json
{
  "nodes": [
    {
      "parameters": {},
      "name": "Start",
      "type": "n8n-nodes-base.manualTrigger",
      "position": [
        250,
        300
      ]
    },
    {
      "parameters": {
        "credentials": {
          "name": "GitHub Enterprise MCP"
        },
        "action": "executeTool",
        "toolName": "list_enterprise_users",
        "toolParameters": {}
      },
      "name": "Get All Users",
      "type": "n8n-nodes-mcp.mcpClient",
      "position": [
        450,
        300
      ]
    },
    {
      "parameters": {
        "mode": "jsonToFile",
        "fileName": "=enterprise-users-report-{{$now.format('YYYY-MM-DD')}}.json",
        "options": {}
      },
      "name": "Write User Report",
      "type": "n8n-nodes-base.writeJsonFile",
      "position": [
        650,
        300
      ]
    }
  ],
  "connections": {
    "Start": {
      "main": [
        [
          {
            "node": "Get All Users",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Get All Users": {
      "main": [
        [
          {
            "node": "Write User Report",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

## Advanced: GitHub Enterprise License Monitoring

This workflow checks enterprise licenses and sends notifications when a license is close to expiration or seat limit.

1. Create a workflow with a **Schedule Trigger** (e.g., daily)
2. Add an **MCP Client** node to call `list_enterprise_licenses`
3. Add a **Split In Batches** node to process each license
4. Add a **Function** node to check license status:

```javascript
// Function node code
const license = items[0].json;
const today = new Date();
const expiresAt = new Date(license.expires_at);
const daysRemaining = Math.floor((expiresAt - today) / (1000 * 60 * 60 * 24));

const seatsUsed = license.seats_used;
const totalSeats = license.seats;
const seatUsagePercent = (seatsUsed / totalSeats) * 100;

return {
  json: {
    ...license,
    daysRemaining,
    seatUsagePercent,
    needsAttention: daysRemaining < 30 || seatUsagePercent > 90
  }
};
```

5. Add an **IF** node to check if the license needs attention
6. Connect to a notification service (e.g., Email, Slack) for alerts

## Example: Automated GitHub User Onboarding

This workflow demonstrates an automated onboarding process for new GitHub Enterprise users:

1. Create a workflow with an **HTTP Request** node as the trigger (webhook)
2. Add a **Set** node to parse the incoming data about the new user
3. Add an **MCP Client** node to call `get_user_info` for existing user check
4. Add an **IF** node to check if the user exists
5. Add another **MCP Client** node to call a custom tool to create the user (if needed)
6. Add an **MCP Client** node to call `list_user_organizations` to verify org access
7. Add a **Send Email** node to notify the user about their GitHub access

## Troubleshooting

### Common Issues

1. **Connection Error**: Ensure the GitHub MCP server is running and accessible from n8n
2. **Authentication Error**: Verify your GitHub token has the required permissions
3. **Tool Not Found**: Make sure the MCP server is properly initialized

### Checking Server Status

You can add a health check workflow:

1. Create a workflow with a **HTTP Request** node
2. Set method to **GET** and URL to `http://github-mcp:8050/health`
3. If the server is running correctly, you should get a 200 response

## Best Practices

### Security

- Store GitHub credentials securely in n8n
- Use dedicated service accounts with minimum required permissions
- Implement IP restrictions if possible

### Performance

- Cache results when appropriate
- Use webhook triggers for real-time responses
- Schedule batch operations during off-peak hours

### Error Handling

- Add error handling in your workflows using the Error Trigger node
- Implement retry mechanisms for transient errors
- Send notifications for critical workflow failures

## Real-World Use Cases

### 1. License Management Dashboard

Create a dashboard that displays:
- License utilization
- Expiration dates
- Cost allocation by department
- Historical usage patterns

### 2. User Activity Reports

Generate reports showing:
- Active vs. inactive users
- Organization membership changes
- Access level modifications
- Login patterns and activity

### 3. Compliance Automation

Automate compliance checks for:
- Access rights reviews
- Orphaned accounts
- Administrative privilege validation
- Security policy adherence

### 4. Cross-System Integration

Connect GitHub Enterprise data with:
- HR systems for onboarding/offboarding
- ITSM platforms for issue tracking
- Identity management systems
- Documentation wikis

## Conclusion

By integrating the GitHub MCP server with n8n, you can create powerful workflows that automate GitHub Enterprise management tasks. This integration enables you to build custom solutions for user management, license tracking, reporting, and much more.

For more information on n8n workflows, visit the [n8n documentation](https://docs.n8n.io/).
