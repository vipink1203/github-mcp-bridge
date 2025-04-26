# main.py
import os
import logging
import asyncio
import aiohttp
import ssl
import certifi
import re
from typing import Dict, List, Optional, Any, AsyncIterator, Tuple
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("github-mcp")

# GitHub API client
class GitHubClient:
    def __init__(self, token: str, enterprise_base_url: str):
        self.token = token
        self.enterprise_base_url = enterprise_base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.session = None
        
        # Setup SSL context with certifi for certificate verification
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())

    async def ensure_session(self):
        """Ensure we have an active session."""
        if self.session is None or self.session.closed:
            conn = aiohttp.TCPConnector(ssl=self.ssl_context)
            self.session = aiohttp.ClientSession(headers=self.headers, connector=conn)
        return self.session

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a GET request to the GitHub Enterprise API."""
        session = await self.ensure_session()
        url = f"{self.enterprise_base_url}{endpoint}"
        
        logger.info(f"Making API request to: {url}")
        
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

    async def get_all_paginated_results(self, endpoint: str, per_page: int = 100) -> Dict:
        """Get all results from a paginated API endpoint."""
        session = await self.ensure_session()
        url = f"{self.enterprise_base_url}{endpoint}"
        all_results = {}
        page = 1
        
        # Start with default structure for the consumed licenses endpoint
        all_results = {
            "total_seats_purchased": 0,
            "total_seats_consumed": 0,
            "seats": []
        }
        
        while True:
            params = {"per_page": per_page, "page": page}
            logger.info(f"Fetching page {page} from: {url}")
            
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        current_page_data = await response.json()
                        
                        # For first page, get the summary information
                        if page == 1:
                            all_results["total_seats_purchased"] = current_page_data.get("total_seats_purchased", 0)
                            all_results["total_seats_consumed"] = current_page_data.get("total_seats_consumed", 0)
                        
                        # Add the users/seats from this page
                        if "seats" in current_page_data:
                            all_results["seats"].extend(current_page_data["seats"])
                        
                        # Check if we're done paginating
                        link_header = response.headers.get("Link", "")
                        if not link_header or 'rel="next"' not in link_header:
                            break
                        
                        # Move to next page
                        page += 1
                    else:
                        text = await response.text()
                        logger.error(f"GitHub API error: {response.status} - {text}")
                        raise Exception(f"GitHub API error: {response.status} - {text}")
            except Exception as e:
                logger.error(f"Error in paginated API request: {str(e)}")
                raise
        
        logger.info(f"Retrieved {len(all_results.get('seats', []))} total entries from {page} pages")
        return all_results

    async def get_consumed_licenses(self, full: bool = True) -> Dict:
        """Get consumed licenses information from the GitHub Enterprise API.
        
        Args:
            full: If True, retrieves all pages of results. If False, retrieves only the first page.
        """
        if full:
            return await self.get_all_paginated_results("/consumed-licenses")
        else:
            return await self.get("/consumed-licenses")

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

# Response models
class LicenseUserDetail(BaseModel):
    """Detailed information about a license user."""
    github_com_login: str
    github_com_name: Optional[str] = None
    license_type: str
    github_com_profile: Optional[str] = None
    github_com_verified_domain_emails: List[str] = []
    github_com_saml_name_id: Optional[str] = None
    github_com_two_factor_auth: Optional[bool] = None

class LicenseSummary(BaseModel):
    """Summary of enterprise license usage."""
    total_seats_consumed: int
    total_seats_purchased: int

class ConsumedLicensesResponse(BaseModel):
    """Complete response for consumed licenses endpoint."""
    summary: LicenseSummary
    users: Optional[List[LicenseUserDetail]] = None

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

    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL")
    if not enterprise_url:
        raise ValueError("GITHUB_ENTERPRISE_URL environment variable is required")
    
    # Ensure the enterprise URL doesn't end with a slash
    if enterprise_url.endswith('/'):
        enterprise_url = enterprise_url[:-1]
    
    github_client = GitHubClient(token=token, enterprise_base_url=enterprise_url)
    
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

@mcp.tool()
async def list_consumed_licenses(ctx: Context, include_users: bool = False, full_pagination: bool = True) -> ConsumedLicensesResponse:
    """
    Get information about consumed licenses in the GitHub Enterprise instance.
    
    This tool retrieves information about license usage in your GitHub Enterprise,
    including the total seats purchased and consumed. Optionally includes detailed
    information about each user consuming a license.
    
    Args:
        include_users: Whether to include detailed user information (default: False)
        full_pagination: Whether to retrieve all pages of results (default: True)
    
    Note: This feature is only available for GitHub Enterprise Cloud customers.
    
    Returns:
        Detailed information about consumed licenses with optional user details.
    """
    global github_client
    
    # Call the consumed-licenses API endpoint with pagination if needed
    consumed_licenses_data = await github_client.get_consumed_licenses(full=full_pagination)
    
    # Create the response with summary information
    response = ConsumedLicensesResponse(
        summary=LicenseSummary(
            total_seats_consumed=consumed_licenses_data.get("total_seats_consumed", 0),
            total_seats_purchased=consumed_licenses_data.get("total_seats_purchased", 0)
        )
    )
    
    # Optionally include detailed user information
    if include_users and "seats" in consumed_licenses_data:
        response.users = [
            LicenseUserDetail(
                github_com_login=user.get("github_com_login", ""),
                github_com_name=user.get("github_com_name"),
                license_type=user.get("license_type", "Unknown"),
                github_com_profile=user.get("github_com_profile"),
                github_com_verified_domain_emails=user.get("github_com_verified_domain_emails", []),
                github_com_saml_name_id=user.get("github_com_saml_name_id"),
                github_com_two_factor_auth=user.get("github_com_two_factor_auth")
            )
            for user in consumed_licenses_data.get("seats", [])
        ]
    
    return response

@mcp.resource("github://consumed-licenses/{dummy}")
async def get_github_consumed_licenses(dummy: str) -> ConsumedLicensesResponse:
    """
    Get detailed information about consumed licenses in the GitHub Enterprise instance.
    
    This resource retrieves information about license usage in your GitHub Enterprise,
    including the total seats purchased and consumed, along with detailed user information.
    
    Note: This feature is only available for GitHub Enterprise Cloud customers.
    
    Returns:
        Detailed information about consumed licenses with user details.
    """
    token = os.environ.get("GITHUB_TOKEN")
    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL")
    
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
        
    if not enterprise_url:
        raise ValueError("GITHUB_ENTERPRISE_URL environment variable is required")
    
    # Ensure the enterprise URL doesn't end with a slash
    if enterprise_url.endswith('/'):
        enterprise_url = enterprise_url[:-1]
    
    # Create a client with SSL configured
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    conn = aiohttp.TCPConnector(ssl=ssl_context)
    session = aiohttp.ClientSession(
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        connector=conn
    )
    
    try:
        # Get all paginated results
        all_results = {
            "total_seats_purchased": 0,
            "total_seats_consumed": 0,
            "seats": []
        }
        
        # Start with page 1
        page = 1
        
        while True:
            params = {"per_page": 100, "page": page}
            url = f"{enterprise_url}/consumed-licenses"
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    current_page_data = await response.json()
                    
                    # For first page, get the summary information
                    if page == 1:
                        all_results["total_seats_purchased"] = current_page_data.get("total_seats_purchased", 0)
                        all_results["total_seats_consumed"] = current_page_data.get("total_seats_consumed", 0)
                    
                    # Add the users/seats from this page
                    if "seats" in current_page_data:
                        all_results["seats"].extend(current_page_data["seats"])
                    
                    # Check if we're done paginating
                    link_header = response.headers.get("Link", "")
                    if not link_header or 'rel="next"' not in link_header:
                        break
                    
                    # Move to next page
                    page += 1
                else:
                    text = await response.text()
                    raise Exception(f"GitHub API error: {response.status} - {text}")
        
        # Create the response with summary information
        resp = ConsumedLicensesResponse(
            summary=LicenseSummary(
                total_seats_consumed=all_results.get("total_seats_consumed", 0),
                total_seats_purchased=all_results.get("total_seats_purchased", 0)
            )
        )
        
        # Include detailed user information
        if "seats" in all_results:
            resp.users = [
                LicenseUserDetail(
                    github_com_login=user.get("github_com_login", ""),
                    github_com_name=user.get("github_com_name"),
                    license_type=user.get("license_type", "Unknown"),
                    github_com_profile=user.get("github_com_profile"),
                    github_com_verified_domain_emails=user.get("github_com_verified_domain_emails", []),
                    github_com_saml_name_id=user.get("github_com_saml_name_id"),
                    github_com_two_factor_auth=user.get("github_com_two_factor_auth")
                )
                for user in all_results.get("seats", [])
            ]
            
        return resp
                
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
    
    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL")
    if enterprise_url:
        logger.info(f"GitHub Enterprise Base URL: {enterprise_url}")
    else:
        logger.warning("No GitHub Enterprise URL found in environment. This is required for operation.")
    
    asyncio.run(main())
