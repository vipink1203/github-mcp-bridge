# main.py
import os
import logging
import asyncio
import aiohttp
import ssl
import certifi
import re
from typing import Dict, List, Optional, Any, Union, AsyncIterator
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("github-mcp")

# GitHub API client
class GitHubClient:
    def __init__(self, token: str, base_url: str = "https://api.github.com", enterprise_name: Optional[str] = None):
        self.token = token
        self.base_url = base_url
        self.enterprise_name = enterprise_name or os.environ.get("GITHUB_ENTERPRISE_NAME")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.session = None
        
        # Setup SSL context with certifi for certificate verification
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Log if we're using GitHub Enterprise
        if self.is_enterprise():
            logger.info(f"Using GitHub Enterprise: {self.enterprise_name}")
        else:
            logger.info("Using GitHub.com API (non-Enterprise)")

    def is_enterprise(self):
        """Check if we're using GitHub Enterprise."""
        return (
            self.enterprise_name is not None or 
            (self.base_url != "https://api.github.com" and "github" in self.base_url.lower())
        )

    async def ensure_session(self):
        if self.session is None or self.session.closed:
            conn = aiohttp.TCPConnector(ssl=self.ssl_context)
            self.session = aiohttp.ClientSession(headers=self.headers, connector=conn)
        return self.session

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """Make a GET request to the GitHub API."""
        session = await self.ensure_session()
        url = f"{self.base_url}/{endpoint}"
        
        logger.info(f"Making API request to: {url}")
        
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    # Log detailed error
                    logger.error(f"GitHub API error: {response.status} - {text}")
                    
                    # Check if it's a 404 and give more helpful error
                    if response.status == 404:
                        if "enterprises" in endpoint and "consumed-licenses" in endpoint:
                            raise Exception(
                                "The consumed-licenses endpoint is only available for GitHub Enterprise Cloud customers. "
                                "Please verify your GitHub Enterprise name and token permissions."
                            )
                        elif "enterprise" in endpoint:
                            raise Exception(
                                "The requested Enterprise endpoint is not available with your current configuration. "
                                "Enterprise endpoints are only available for GitHub Enterprise customers."
                            )
                    
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

class ConsumedLicense(BaseModel):
    """GitHub consumed license model."""
    user_login: str
    user_id: int
    user_type: str
    user_name: Optional[str] = None
    email: Optional[str] = None
    saml_name_id: Optional[str] = None
    github_com_enterprise_name: Optional[str] = None
    created_at: str
    updated_at: str

# Global client instance for tools
github_client = None

# Lifespan context manager for the MCP server
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Manage application lifecycle."""
    global github_client
    
    # Initialize resources on startup
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL", "https://api.github.com")
    enterprise_name = os.environ.get("GITHUB_ENTERPRISE_NAME")
    
    github_client = GitHubClient(token=token, base_url=enterprise_url, enterprise_name=enterprise_name)
    
    try:
        # Set up the application context
        yield None
    finally:
        # Clean up resources on shutdown
        await github_client.close()

# Initialize the MCP server with lifespan support
mcp = FastMCP(
    "GitHub Enterprise MCP",
    lifespan=app_lifespan
)

# MCP tools for GitHub Enterprise users
@mcp.tool()
async def list_enterprise_users(ctx: Context) -> List[User]:
    """
    List all users in the GitHub Enterprise instance.
    
    Returns:
        A list of users in the enterprise.
    """
    global github_client
    
    if not github_client.is_enterprise():
        raise ValueError("This tool can only be used with GitHub Enterprise. Set GITHUB_ENTERPRISE_NAME environment variable.")
    
    try:
        # Try the endpoint most common in GitHub Enterprise Cloud
        response = await github_client.get("enterprises/{}/members".format(github_client.enterprise_name))
        return [User(**user) for user in response]
    except Exception as e:
        if "404" in str(e):
            try:
                # Fallback to the older API endpoint
                response = await github_client.get("enterprise/users")
                return [User(**user) for user in response]
            except Exception as fallback_e:
                # If both fail, try a general users endpoint
                try:
                    response = await github_client.get("users")
                    return [User(**user) for user in response]
                except:
                    # Re-raise the original enterprise-specific error
                    raise e
        else:
            raise

@mcp.tool()
async def get_user_info(ctx: Context, username: str) -> User:
    """
    Get detailed information for a specific GitHub user.
    
    Args:
        username: The GitHub username to look up.
        
    Returns:
        Detailed user information.
    """
    global github_client
    user_data = await github_client.get(f"users/{username}")
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
    global github_client
    orgs_data = await github_client.get(f"users/{username}/orgs")
    return [Organization(**org) for org in orgs_data]

@mcp.tool()
async def list_enterprise_organizations(ctx: Context) -> List[Organization]:
    """
    List all organizations in the GitHub Enterprise instance.
    
    Returns:
        A list of organizations in the enterprise.
    """
    global github_client
    
    if not github_client.is_enterprise() and github_client.enterprise_name:
        try:
            # Try enterprise-specific endpoint
            orgs_data = await github_client.get(f"enterprises/{github_client.enterprise_name}/organizations")
            return [Organization(**org) for org in orgs_data]
        except Exception as e:
            if "404" in str(e):
                # Fall back to general organizations endpoint
                orgs_data = await github_client.get("organizations")
                return [Organization(**org) for org in orgs_data]
            else:
                raise
    else:
        # Use general organizations endpoint
        orgs_data = await github_client.get("organizations")
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
    global github_client
    # This endpoint requires admin access for enterprise users
    emails_data = await github_client.get(f"users/{username}/emails")
    return [Email(**email) for email in emails_data]

@mcp.tool()
async def list_enterprise_licenses(ctx: Context) -> List[License]:
    """
    List all licenses in the GitHub Enterprise instance.
    
    Returns:
        A list of licenses in the enterprise.
    """
    global github_client
    
    if not github_client.is_enterprise():
        raise ValueError("This tool can only be used with GitHub Enterprise. Set GITHUB_ENTERPRISE_NAME environment variable.")
    
    try:
        # Try enterprise-specific endpoint
        if github_client.enterprise_name:
            licenses_data = await github_client.get(f"enterprises/{github_client.enterprise_name}/licenses")
        else:
            licenses_data = await github_client.get("enterprise/licenses")
        
        return [License(**license) for license in licenses_data]
    except Exception as e:
        if "404" in str(e):
            raise ValueError(
                "License information is only available for GitHub Enterprise customers with appropriate permissions. "
                "Please verify your GitHub Enterprise configuration and token permissions."
            )
        raise

@mcp.tool()
async def get_license_info(ctx: Context, id: str) -> License:
    """
    Get detailed information for a specific license.
    
    Args:
        id: The license ID to look up.
        
    Returns:
        Detailed license information.
    """
    global github_client
    
    if not github_client.is_enterprise():
        raise ValueError("This tool can only be used with GitHub Enterprise. Set GITHUB_ENTERPRISE_NAME environment variable.")
    
    try:
        # Try enterprise-specific endpoint
        if github_client.enterprise_name:
            license_data = await github_client.get(f"enterprises/{github_client.enterprise_name}/licenses/{id}")
        else:
            license_data = await github_client.get(f"enterprise/licenses/{id}")
        
        return License(**license_data)
    except Exception as e:
        if "404" in str(e):
            raise ValueError(
                "License information is only available for GitHub Enterprise customers with appropriate permissions. "
                "Please verify your GitHub Enterprise configuration and token permissions."
            )
        raise

@mcp.tool()
async def list_consumed_licenses(ctx: Context) -> List[ConsumedLicense]:
    """
    List all consumed licenses in the GitHub Enterprise instance.
    
    This tool retrieves detailed information about each license that has been 
    consumed in your GitHub Enterprise, including user information, email, 
    and SAML identities where available.
    
    Note: This feature is only available for GitHub Enterprise Cloud customers.
    
    Returns:
        A list of consumed licenses with detailed user information.
    """
    global github_client
    
    if not github_client.enterprise_name:
        raise ValueError(
            "GITHUB_ENTERPRISE_NAME environment variable is required for this operation. "
            "Consumed licenses API is only available for GitHub Enterprise Cloud customers."
        )
    
    try:
        # Try the Enterprise Cloud endpoint
        consumed_licenses_data = await github_client.get(f"enterprises/{github_client.enterprise_name}/consumed-licenses")
        return [ConsumedLicense(**license) for license in consumed_licenses_data.get("seats", [])]
    except Exception as e:
        if "404" in str(e):
            # Give a more helpful error message
            raise ValueError(
                "The consumed-licenses endpoint is only available for GitHub Enterprise Cloud customers. "
                "Please verify your GitHub Enterprise name and token permissions. "
                "This feature may not be available on your GitHub plan."
            )
        raise

# Create a configured SSL context for resource functions 
def get_ssl_connector():
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    return aiohttp.TCPConnector(ssl=ssl_context)

# MCP resources for GitHub Enterprise
# Note: For resources, we cannot use ctx parameter without URI params
@mcp.resource("github://users/{dummy}")
async def get_github_users(dummy: str) -> List[User]:
    """
    Get a list of all GitHub Enterprise users.
    
    Returns:
        A list of all users in the enterprise.
    """
    # Access client from the global scope
    token = os.environ.get("GITHUB_TOKEN")
    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL", "https://api.github.com")
    enterprise_name = os.environ.get("GITHUB_ENTERPRISE_NAME")
    
    # Create a client with SSL configured
    conn = get_ssl_connector()
    session = aiohttp.ClientSession(
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        connector=conn
    )
    
    try:
        # Try different endpoints in order of likelihood
        endpoints = []
        
        if enterprise_name:
            endpoints.append(f"{enterprise_url}/enterprises/{enterprise_name}/members")
        
        endpoints.append(f"{enterprise_url}/enterprise/users")
        endpoints.append(f"{enterprise_url}/users")
        
        for endpoint in endpoints:
            try:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [User(**user) for user in data]
            except:
                continue
                
        # If all endpoints fail, raise an error
        raise Exception("Could not retrieve GitHub users. Please check your token permissions.")
    finally:
        await session.close()

@mcp.resource("github://organizations/{dummy}")
async def get_github_organizations(dummy: str) -> List[Organization]:
    """
    Get a list of all GitHub Enterprise organizations.
    
    Returns:
        A list of all organizations in the enterprise.
    """
    token = os.environ.get("GITHUB_TOKEN")
    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL", "https://api.github.com")
    enterprise_name = os.environ.get("GITHUB_ENTERPRISE_NAME")
    
    # Create a client with SSL configured
    conn = get_ssl_connector()
    session = aiohttp.ClientSession(
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        connector=conn
    )
    
    try:
        # Try different endpoints in order of likelihood
        endpoints = []
        
        if enterprise_name:
            endpoints.append(f"{enterprise_url}/enterprises/{enterprise_name}/organizations")
        
        endpoints.append(f"{enterprise_url}/organizations")
        
        for endpoint in endpoints:
            try:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [Organization(**org) for org in data]
            except:
                continue
                
        # If all endpoints fail, raise an error
        raise Exception("Could not retrieve GitHub organizations. Please check your token permissions.")
    finally:
        await session.close()

@mcp.resource("github://user/{username}")
async def get_github_user(username: str) -> User:
    """
    Get information about a specific GitHub user.
    
    Args:
        username: The GitHub username to look up.
        
    Returns:
        Detailed user information.
    """
    token = os.environ.get("GITHUB_TOKEN")
    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL", "https://api.github.com")
    
    # Create a client with SSL configured
    conn = get_ssl_connector()
    session = aiohttp.ClientSession(
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        connector=conn
    )
    
    try:
        async with session.get(f"{enterprise_url}/users/{username}") as response:
            if response.status == 200:
                data = await response.json()
                return User(**data)
            else:
                text = await response.text()
                raise Exception(f"GitHub API error: {response.status} - {text}")
    finally:
        await session.close()

@mcp.resource("github://user/{username}/organizations")
async def get_github_user_organizations(username: str) -> List[Organization]:
    """
    Get organizations for a specific GitHub user.
    
    Args:
        username: The GitHub username to look up organizations for.
        
    Returns:
        A list of organizations the user belongs to.
    """
    token = os.environ.get("GITHUB_TOKEN")
    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL", "https://api.github.com")
    
    # Create a client with SSL configured
    conn = get_ssl_connector()
    session = aiohttp.ClientSession(
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        connector=conn
    )
    
    try:
        async with session.get(f"{enterprise_url}/users/{username}/orgs") as response:
            if response.status == 200:
                data = await response.json()
                return [Organization(**org) for org in data]
            else:
                text = await response.text()
                raise Exception(f"GitHub API error: {response.status} - {text}")
    finally:
        await session.close()

@mcp.resource("github://licenses/{dummy}")
async def get_github_licenses(dummy: str) -> List[License]:
    """
    Get a list of all GitHub Enterprise licenses.
    
    Returns:
        A list of all licenses in the enterprise.
    """
    token = os.environ.get("GITHUB_TOKEN")
    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL", "https://api.github.com")
    enterprise_name = os.environ.get("GITHUB_ENTERPRISE_NAME")
    
    if not enterprise_name:
        raise ValueError(
            "GITHUB_ENTERPRISE_NAME environment variable is required for this operation. "
            "License information is only available for GitHub Enterprise customers."
        )
    
    # Create a client with SSL configured
    conn = get_ssl_connector()
    session = aiohttp.ClientSession(
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        connector=conn
    )
    
    try:
        # Try different endpoints in order of likelihood
        endpoints = [
            f"{enterprise_url}/enterprises/{enterprise_name}/licenses",
            f"{enterprise_url}/enterprise/licenses"
        ]
        
        for endpoint in endpoints:
            try:
                async with session.get(endpoint) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [License(**license) for license in data]
            except:
                continue
                
        # If all endpoints fail, raise an error
        raise ValueError(
            "License information is only available for GitHub Enterprise customers with appropriate permissions. "
            "Please verify your GitHub Enterprise configuration and token permissions."
        )
    finally:
        await session.close()

@mcp.resource("github://consumed-licenses/{dummy}")
async def get_github_consumed_licenses(dummy: str) -> List[ConsumedLicense]:
    """
    Get a list of all consumed licenses in the GitHub Enterprise instance.
    
    This resource retrieves detailed information about each license that has been 
    consumed in your GitHub Enterprise, including user information, email, 
    and SAML identities where available.
    
    Note: This feature is only available for GitHub Enterprise Cloud customers.
    
    Returns:
        A list of consumed licenses with detailed user information.
    """
    token = os.environ.get("GITHUB_TOKEN")
    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL", "https://api.github.com")
    enterprise_name = os.environ.get("GITHUB_ENTERPRISE_NAME")
    
    if not enterprise_name:
        raise ValueError(
            "GITHUB_ENTERPRISE_NAME environment variable is required for this operation. "
            "Consumed licenses API is only available for GitHub Enterprise Cloud customers."
        )
    
    # Create a client with SSL configured
    conn = get_ssl_connector()
    session = aiohttp.ClientSession(
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        connector=conn
    )
    
    try:
        endpoint = f"{enterprise_url}/enterprises/{enterprise_name}/consumed-licenses"
        
        async with session.get(endpoint) as response:
            if response.status == 200:
                data = await response.json()
                return [ConsumedLicense(**license) for license in data.get("seats", [])]
            elif response.status == 404:
                raise ValueError(
                    "The consumed-licenses endpoint is only available for GitHub Enterprise Cloud customers. "
                    "Please verify your GitHub Enterprise name and token permissions. "
                    "This feature may not be available on your GitHub plan."
                )
            else:
                text = await response.text()
                raise Exception(f"GitHub API error: {response.status} - {text}")
    finally:
        await session.close()

# Define an async main function
async def main():
    # Get the transport type from environment variables (default to stdio)
    transport = os.environ.get("TRANSPORT", "stdio").lower()
    
    # Configure server based on transport type
    if transport == "sse":
        import uvicorn
        from starlette.applications import Starlette
        from starlette.routing import Mount
        
        # Create a Starlette application with the SSE server mounted at the root
        app = Starlette(
            routes=[
                Mount("/", app=mcp.sse_app()),
            ]
        )
        
        # Start the ASGI server
        port = int(os.environ.get("PORT", 8050))
        host = os.environ.get("HOST", "0.0.0.0")
        
        logger.info(f"Starting SSE server on {host}:{port}")
        uvicorn.run(app, host=host, port=port)
    else:  # Default to stdio
        logger.info("Starting server with stdio transport")
        await mcp.run_stdio_async()

# Main entry point
if __name__ == "__main__":
    # Make sure certifi is available
    try:
        certifi_path = certifi.where()
        logger.info(f"Using SSL certificates from: {certifi_path}")
    except ImportError:
        logger.warning("certifi package not found. SSL verification may fail.")
    
    # Log environment
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        logger.info("GitHub token found in environment")
    else:
        logger.warning("No GitHub token found in environment")
    
    enterprise_name = os.environ.get("GITHUB_ENTERPRISE_NAME")
    if enterprise_name:
        logger.info(f"GitHub Enterprise name: {enterprise_name}")
    else:
        logger.warning("No GitHub Enterprise name found in environment. Some enterprise features may not be available.")
    
    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL", "https://api.github.com")
    logger.info(f"GitHub API URL: {enterprise_url}")
    
    asyncio.run(main())
