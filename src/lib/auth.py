import time
import logging
import aiohttp
from typing import Optional
from .config import settings

logger = logging.getLogger("myride.auth")

class AuthManager:
    def __init__(self, refresh_token: Optional[str] = None):
        configured_ref = settings.myride_refresh_token
        if configured_ref and "your_cognito_refresh_token" in configured_ref:
            configured_ref = None

        self.refresh_token = refresh_token or configured_ref
        self.access_token: Optional[str] = None
        self.id_token: Optional[str] = None
        self.expires_at: float = 0.0

    def set_tokens(self, access_token: str, refresh_token: Optional[str] = None, expires_in: int = 3600, id_token: Optional[str] = None):
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        if id_token:
            self.id_token = id_token
        self.expires_at = time.time() + expires_in - 60
        logger.info("Access token updated. Expires in %s seconds.", expires_in)

    def is_token_valid(self) -> bool:
        return bool(self.access_token and time.time() < self.expires_at)

    async def get_valid_access_token(self, session: Optional[aiohttp.ClientSession] = None) -> str:
        if self.is_token_valid():
            return self.access_token

        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            # 1. Try Refresh Token if available
            if self.refresh_token:
                try:
                    return await self.refresh_access_token(session)
                except Exception as e:
                    logger.warning("Refresh token auth failed (%s). Attempting credential login...", e)

            # 2. Fall back to Username & Password Authentication
            if settings.myride_username and settings.myride_password:
                return await self.login_with_credentials(
                    settings.myride_username,
                    settings.myride_password,
                    session
                )

            raise ValueError("No valid token, refresh token, or username/password credentials provided.")
        finally:
            if close_session:
                await session.close()

    async def refresh_access_token(self, session: Optional[aiohttp.ClientSession] = None) -> str:
        if not self.refresh_token:
            raise ValueError("Cannot refresh access token: refresh_token is missing.")

        url = f"https://{settings.cognito_domain}/oauth2/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": settings.cognito_client_id,
            "refresh_token": self.refresh_token,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            logger.info("Refreshing access token via Cognito endpoint...")
            async with session.post(url, data=payload, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Failed to refresh token (Status {resp.status}): {text}")

                data = await resp.json()
                access_token = data.get("access_token")
                new_refresh_token = data.get("refresh_token", self.refresh_token)
                expires_in = data.get("expires_in", 3600)
                id_token = data.get("id_token")

                self.set_tokens(
                    access_token=access_token,
                    refresh_token=new_refresh_token,
                    expires_in=expires_in,
                    id_token=id_token
                )
                return access_token
        finally:
            if close_session:
                await session.close()

    async def login_with_credentials(self, username: str, password: str, session: Optional[aiohttp.ClientSession] = None) -> str:
        url = "https://cognito-idp.us-east-1.amazonaws.com"
        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"
        }
        payload = {
            "AuthFlow": "USER_PASSWORD_AUTH",
            "ClientId": settings.cognito_client_id,
            "AuthParameters": {
                "USERNAME": username,
                "PASSWORD": password
            }
        }

        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            logger.info("Authenticating with username and password for %s...", username)
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Cognito credential authentication failed (Status {resp.status}): {text}")

                data = await resp.json(content_type=None)
                auth_res = data.get("AuthenticationResult", {})
                access_token = auth_res.get("AccessToken")
                refresh_token = auth_res.get("RefreshToken")
                id_token = auth_res.get("IdToken")
                expires_in = auth_res.get("ExpiresIn", 3600)

                if not access_token:
                    raise Exception(f"Authentication response missing AccessToken: {data}")

                self.set_tokens(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=expires_in,
                    id_token=id_token
                )
                logger.info("Successfully authenticated with username/password!")
                return access_token
        finally:
            if close_session:
                await session.close()
