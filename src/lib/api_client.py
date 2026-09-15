import logging
import aiohttp
from typing import Optional, Dict, Any, List
from .config import settings

logger = logging.getLogger("myride.api")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Origin": "https://myridek12.tylerapp.com",
    "Referer": "https://myridek12.tylerapp.com/",
    "x-client-language": "en",
    "x-client-version": "2026.3.35+faa0e3",
    "x-device-type": "browser",
    "x-requested-with": "XMLHttpRequest",
    "x-signalr-user-agent": "Microsoft SignalR/10.0 (10.0.0+b0f34d51fccc69fd334253924abd8d6853fad7aa; Unknown OS; .NET; .NET 10.0.11)",
}

class MyRideAPIClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.api_base_url

    async def get_user_info(self, access_token: str, session: Optional[aiohttp.ClientSession] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/user"
        headers = {
            **DEFAULT_HEADERS,
            "Authorization": f"Bearer {access_token}"
        }
        
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            logger.info("Fetching user info from %s", url)
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Failed to fetch user info (Status {resp.status}): {text}")
                data = await resp.json()
                return data
        finally:
            if close_session:
                await session.close()

    async def get_student_info(self, access_token: str, tenant_id: str, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/student"
        headers = {
            **DEFAULT_HEADERS,
            "Authorization": f"Bearer {access_token}",
            "x-tenant-id": tenant_id
        }

        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            logger.info("Fetching student info from %s with tenant_id %s", url, tenant_id)
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Failed to fetch student info (Status {resp.status}): {text}")
                data = await resp.json()
                return data
        finally:
            if close_session:
                await session.close()

    async def negotiate_signalr(self, access_token: str, tenant_id: str, session: Optional[aiohttp.ClientSession] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/livevehiclehub/negotiate"
        params = {
            "x-tenant-id": tenant_id,
            "negotiateVersion": "1"
        }
        headers = {
            **DEFAULT_HEADERS,
            "Authorization": f"Bearer {access_token}",
            "x-tenant-id": tenant_id
        }

        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            logger.info("Negotiating SignalR connection at %s", url)
            async with session.post(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"SignalR negotiate failed (Status {resp.status}): {text}")
                data = await resp.json()
                return data
        finally:
            if close_session:
                await session.close()
