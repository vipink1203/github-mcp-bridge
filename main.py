import os
import logging
import asyncio
import aiohttp
import ssl
import certifi
import re
from typing import Dict, List, Optional, Any, AsyncIterator
from contextlib import asynccontextmanager

from cachetools import TTLCache, cached
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, root_validator

# ——— TROUBLESHOOTING: confirm this file loads ———
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("github-mcp")
logger.info("🔥 Loading GitHub Enterprise MCP from main.py 🔥")

# --- Helpers --------------------------------------------------------------

def parse_next_link(link_header: str) -> Optional[str]:
    for part in link_header.split(","):
        url_part, *params = part.split(";")
        url = url_part.strip().strip("<>")
        for param in params:
            if 'rel="next"' in param:
                return url
    return None

# --- GitHub Client --------------------------------------------------------

class GitHubClient:
    def __init__(self, token: str, enterprise_base_url: str):
        self.token = token
        self.base = enterprise_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.session: Optional[aiohttp.ClientSession] = None

    async def ensure_session(self) -> aiohttp.ClientSession:
        if not self.session or self.session.closed:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            self.session = aiohttp.ClientSession(headers=self.headers, connector=connector)
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(min=1, max=10),
            reraise=True
        ):
            with attempt:
                session = await self.ensure_session()
                resp = await session.request(method, url, **kwargs)
                if resp.status in (429, 500, 502, 503, 504):
                    text = await resp.text()
                    logger.warning(f"Retryable error {resp.status}: {text}")
                    resp.release()
                    raise aiohttp.ClientResponseError(
                        resp.request_info, resp.history,
                        status=resp.status, message=text
                    )
                return resp

    async def get_all_paginated_results(self, endpoint: str, per_page: int = 100) -> Dict[str, Any]:
        url = f"{self.base}{endpoint}"
        all_data: Dict[str, Any] = {
            "total_seats_purchased": 0,
            "total_seats_consumed": 0,
            "users": []
        }
        next_url = f"{url}?per_page={per_page}&page=1"

        while next_url:
            resp = await self._request_with_retry("GET", next_url)
            data = await resp.json()
            if not all_data["total_seats_purchased"]:
                all_data["total_seats_purchased"] = data.get("total_seats_purchased", 0)
                all_data["total_seats_consumed"] = data.get("total_seats_consumed", 0)

            all_data["users"].extend(data.get("users", []))
            link = resp.headers.get("Link", "")
            next_url = parse_next_link(link)

        logger.info(f"Fetched {len(all_data['users'])} users across licenses")
        return all_data

    _license_cache = TTLCache(maxsize=1, ttl=3 * 60 * 60)

    @cached(_license_cache)
    async def _fetch_consumed_licenses(self) -> Dict[str, Any]:
        return await self.get_all_paginated_results("/consumed-licenses")

    async def fetch_consumed_licenses(self, full: bool = True) -> Dict[str, Any]:
        if full:
            return await self._fetch_consumed_licenses()
        resp = await self._request_with_retry("GET", f"{self.base}/consumed-licenses")
        return await resp.json()

# --- Pydantic Models ------------------------------------------------------

class UserOrganization(BaseModel):
    organization: str
    role: str

def parse_member_roles(roles: List[str]) -> List[UserOrganization]:
    out: List[UserOrganization] = []
    for r in roles:
        if ":" in r:
            org, role = r.split(":", 1)
            out.append(UserOrganization(organization=org, role=role))
    return out

class LicenseUserDetail(BaseModel):
    github_com_login: str
    github_com_name: Optional[str] = None
    license_type: str
    github_com_profile: Optional[str] = None
    github_com_verified_domain_emails: List[str] = Field(default_factory=list)
    github_com_saml_name_id: Optional[str] = None
    github_com_two_factor_auth: Optional[bool] = None
    github_com_user: Optional[bool] = None
    enterprise_server_user: Optional[bool] = None
    visual_studio_subscription_user: Optional[bool] = None
    enterprise_server_user_ids: List[str] = Field(default_factory=list)
    github_com_member_roles: List[str] = Field(default_factory=list)
    github_com_enterprise_roles: List[str] = Field(default_factory=list, alias="github_com_enterprise_roles")
    github_com_enterprise_role: Optional[str] = Field(None, alias="github_com_enterprise_role")
    github_com_orgs_with_pending_invites: List[str] = Field(default_factory=list)
    enterprise_server_emails: List[str] = Field(default_factory=list)
    visual_studio_license_status: Optional[str] = None
    visual_studio_subscription_email: Optional[str] = None
    total_user_accounts: Optional[int] = None

    @root_validator(pre=True)
    def unify_enterprise_roles(cls, values):
        single = values.get("github_com_enterprise_role")
        plural = values.get("github_com_enterprise_roles", [])
        if single and single not in plural:
            plural.append(single)
        values["github_com_enterprise_roles"] = plural
        return values

    class Config:
        allow_population_by_field_name = True

class LicenseSummary(BaseModel):
    total_seats_consumed: int
    total_seats_purchased: int

class ConsumedLicensesResponse(BaseModel):
    summary: LicenseSummary
    users: Optional[List[LicenseUserDetail]] = None

# --- MCP Server Setup -----------------------------------------------------

github_client: Optional[GitHubClient] = None

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    global github_client
    token = os.getenv("GITHUB_TOKEN")
    url   = os.getenv("GITHUB_ENTERPRISE_URL")
    if not token or not url:
        raise ValueError("GITHUB_TOKEN and GITHUB_ENTERPRISE_URL are required")
    github_client = GitHubClient(token, url)
    try:
        yield
    finally:
        await github_client.close()

mcp = FastMCP("GitHub Enterprise MCP", lifespan=app_lifespan)

# --- Tools / Resources ----------------------------------------------------

@mcp.tool()
async def list_consumed_licenses(
    ctx: Context,
    include_users: bool = False,
    full_pagination: bool = True
) -> ConsumedLicensesResponse:
    data = await github_client.fetch_consumed_licenses(full_pagination)
    resp = ConsumedLicensesResponse(
        summary=LicenseSummary(
            total_seats_consumed=data.get("total_seats_consumed", 0),
            total_seats_purchased=data.get("total_seats_purchased", 0),
        )
    )
    if include_users:
        resp.users = [LicenseUserDetail(**u) for u in data.get("users", [])]
    return resp

@mcp.tool()
async def get_user_organizations(
    ctx: Context,
    username: str,
    full_pagination: bool = True
) -> List[UserOrganization]:
    if not username:
        raise ValueError("username is required")
    data = await github_client.fetch_consumed_licenses(full_pagination)
    for u in data.get("users", []):
        if u.get("github_com_login") == username:
            return parse_member_roles(u.get("github_com_member_roles", []))
    raise ValueError(f"User '{username}' not found")

@mcp.tool()
async def get_user_enterprise_roles(
    ctx: Context,
    username: str,
    full_pagination: bool = True
) -> List[str]:
    if not username:
        raise ValueError("username is required")
    data = await github_client.fetch_consumed_licenses(full_pagination)
    for u in data.get("users", []):
        if u.get("github_com_login") == username:
            return u.get("github_com_enterprise_roles", [])
    raise ValueError(f"User '{username}' not found")

@mcp.tool()
async def get_user_detail(
    ctx: Context,
    username: str,
    full_pagination: bool = True
) -> LicenseUserDetail:
    if not username:
        raise ValueError("username is required")
    data = await github_client.fetch_consumed_licenses(full_pagination)
    for u in data.get("users", []):
        if u.get("github_com_login") == username:
            return LicenseUserDetail(**u)
    raise ValueError(f"User '{username}' not found")

@mcp.resource("github://consumed-licenses/{dummy}")
async def get_github_consumed_licenses(dummy: str) -> ConsumedLicensesResponse:
    return await list_consumed_licenses(None, include_users=True, full_pagination=True)

@mcp.resource("github://user/{username}/roles")
async def get_github_user_roles(username: str) -> Dict[str, Any]:
    orgs  = await get_user_organizations(None, username, True)
    roles = await get_user_enterprise_roles(None, username, True)
    return {"organizations": orgs, "enterprise_roles": roles}

# ——— TROUBLESHOOTING: dump what got registered ———
logger.info(f"Registered tools: {list(mcp.tools.keys())}")
logger.info(f"Registered resources: {list(mcp.resources.keys())}")

# --- Main -------------------------------------------------------------

async def main():
    transport = os.getenv("TRANSPORT", "stdio").lower()
    if transport == "sse":
        import uvicorn
        from starlette.applications import Starlette
        from starlette.routing import Mount
        app = Starlette(routes=[Mount("/", app=mcp.sse_app())])
        uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8050)))
    else:
        await mcp.run_stdio_async()

if __name__ == "__main__":
    try:
        cert_path = certifi.where()
        logger.info(f"SSL certs from: {cert_path}")
    except ImportError:
        logger.warning("certifi not installed; SSL may not verify")
    if not os.getenv("GITHUB_TOKEN") or not os.getenv("GITHUB_ENTERPRISE_URL"):
        logger.error("Missing required env vars")
    asyncio.run(main())
