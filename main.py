# main.py
import os
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Union
from mcp.server.fastmcp import FastMCP, Resource, Context
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("github-mcp")

# Initialize the MCP server
mcp = FastMCP("GitHub Enterprise MCP")

# GitHub API client
class GitHubClient:
    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.session = None

    async def ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Make a GET request to the GitHub API."""
        session = await self.ensure_session()
        url = f"{self.base_url}/{endpoint}"
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    logger.error(f"GitHub API error: {response.status} - {text}")
                    raise Exception(f"GitHub API error: {response.status} - {text}")
        except Exception as e:
            logger.error(f"Error in GitHub API request: {str(e)}")
            raise

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

# Response models
class User(BaseModel):
    """GitHub user model."""
    login: str
    id: int
    avatar_url: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    type: str
    site_admin: bool
    created_at: str
    updated_at: str

class Email(BaseModel):
    """GitHub email model."""
    email: str
    primary: bool
    verified: bool
    visibility: Optional[str] = None

class Organization(BaseModel):
    """GitHub organization model."""
    login: str
    id: int
    url: str
    description: Optional[str] = None
    name: Optional[str] = None

class License(BaseModel):
    """GitHub license model."""
    id: str
    type: str
    seats: int
    seats_used: int
    expires_at: Optional[str] = None
    created_at: str
    updated_at: str

# Context manager for the application
class AppContext:
    """Application context for the GitHub MCP server."""
    def __init__(self, github_client: GitHubClient):
        self.github_client = github_client

# Initialize the GitHub client with token from environment variables
@mcp.startup
async def startup():
    """Initialize resources on startup."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL", "https://api.github.com")
    
    github_client = GitHubClient(token=token, base_url=enterprise_url)
    
    # Set up the application context
    return AppContext(github_client=github_client)

@mcp.shutdown
async def shutdown(context: AppContext):
    """Clean up resources on shutdown."""
    await context.github_client.close()

# MCP tools for GitHub Enterprise users
@mcp.tool()
async def list_enterprise_users(ctx: Context) -> List[User]:
    """
    List all users in the GitHub Enterprise instance.
    
    Returns:
        A list of users in the enterprise.
    """
    client = ctx.app.github_client
    response = await client.get("enterprise/users")
    return [User(**user) for user in response]

@mcp.tool()
async def get_user_info(ctx: Context, username: str) -> User:
    """
    Get detailed information for a specific GitHub user.
    
    Args:
        username: The GitHub username to look up.
        
    Returns:
        Detailed user information.
    """
    client = ctx.app.github_client
    user_data = await client.get(f"users/{username}")
    return User(**user_data)

@mcp.tool()
async def list_user_organizations(ctx: Context, username: str) -> List[Organization]:
    """
    Get all organizations that a user belongs to.
    
    Args:
        username: The GitHub username to look up organizations for.
        
    Returns:
        A list of organizations the user belongs to.
    """
    client = ctx.app.github_client
    orgs_data = await client.get(f"users/{username}/orgs")
    return [Organization(**org) for org in orgs_data]

@mcp.tool()
async def list_enterprise_organizations(ctx: Context) -> List[Organization]:
    """
    List all organizations in the GitHub Enterprise instance.
    
    Returns:
        A list of organizations in the enterprise.
    """
    client = ctx.app.github_client
    orgs_data = await client.get("organizations")
    return [Organization(**org) for org in orgs_data]

@mcp.tool()
async def get_user_emails(ctx: Context, username: str) -> List[Email]:
    """
    Get all email addresses for a user.
    
    Args:
        username: The GitHub username to look up emails for.
        
    Returns:
        A list of email addresses for the user.
    """
    client = ctx.app.github_client
    # This endpoint requires admin access for enterprise users
    emails_data = await client.get(f"users/{username}/emails")
    return [Email(**email) for email in emails_data]

@mcp.tool()
async def list_enterprise_licenses(ctx: Context) -> List[License]:
    """
    List all licenses in the GitHub Enterprise instance.
    
    Returns:
        A list of licenses in the enterprise.
    """
    client = ctx.app.github_client
    licenses_data = await client.get("enterprise/licenses")
    return [License(**license) for license in licenses_data]

@mcp.tool()
async def get_license_info(ctx: Context, id: str) -> License:
    """
    Get detailed information for a specific license.
    
    Args:
        id: The license ID to look up.
        
    Returns:
        Detailed license information.
    """
    client = ctx.app.github_client
    license_data = await client.get(f"enterprise/licenses/{id}")
    return License(**license_data)

# MCP resources for GitHub Enterprise
@mcp.resource("github://users")
async def get_github_users(ctx: Context) -> List[User]:
    """
    Get a list of all GitHub Enterprise users.
    
    Returns:
        A list of all users in the enterprise.
    """
    client = ctx.app.github_client
    response = await client.get("enterprise/users")
    return [User(**user) for user in response]

@mcp.resource("github://organizations")
async def get_github_organizations(ctx: Context) -> List[Organization]:
    """
    Get a list of all GitHub Enterprise organizations.
    
    Returns:
        A list of all organizations in the enterprise.
    """
    client = ctx.app.github_client
    orgs_data = await client.get("organizations")
    return [Organization(**org) for org in orgs_data]

@mcp.resource("github://user/{username}")
async def get_github_user(ctx: Context, username: str) -> User:
    """
    Get information about a specific GitHub user.
    
    Args:
        username: The GitHub username to look up.
        
    Returns:
        Detailed user information.
    """
    client = ctx.app.github_client
    user_data = await client.get(f"users/{username}")
    return User(**user_data)

@mcp.resource("github://user/{username}/organizations")
async def get_github_user_organizations(ctx: Context, username: str) -> List[Organization]:
    """
    Get organizations for a specific GitHub user.
    
    Args:
        username: The GitHub username to look up organizations for.
        
    Returns:
        A list of organizations the user belongs to.
    """
    client = ctx.app.github_client
    orgs_data = await client.get(f"users/{username}/orgs")
    return [Organization(**org) for org in orgs_data]

@mcp.resource("github://licenses")
async def get_github_licenses(ctx: Context) -> List[License]:
    """
    Get a list of all GitHub Enterprise licenses.
    
    Returns:
        A list of all licenses in the enterprise.
    """
    client = ctx.app.github_client
    licenses_data = await client.get("enterprise/licenses")
    return [License(**license) for license in licenses_data]

# Main entry point
if __name__ == "__main__":
    # Get the transport type from environment variables (default to stdio)
    transport = os.environ.get("TRANSPORT", "stdio").lower()
    
    # Configure server based on transport type
    if transport == "sse":
        port = int(os.environ.get("PORT", 8050))
        host = os.environ.get("HOST", "0.0.0.0")
        mcp.run(host=host, port=port)
    else:  # Default to stdio
        mcp.run_stdio()
