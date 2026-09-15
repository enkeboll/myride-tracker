import pytest
import time
from unittest.mock import patch
from auth import AuthManager

def test_auth_manager_initialization():
    auth = AuthManager(refresh_token="test_refresh_token")
    assert auth.refresh_token == "test_refresh_token"
    assert not auth.is_token_valid()

def test_set_tokens():
    auth = AuthManager(refresh_token="test_refresh_token")
    auth.set_tokens(access_token="test_access_token", expires_in=3600)
    assert auth.is_token_valid()
    assert auth.access_token == "test_access_token"
    assert auth.expires_at > time.time()

@pytest.mark.asyncio
async def test_get_valid_access_token_raises_without_credentials():
    auth = AuthManager(refresh_token=None)
    with patch("config.settings.myride_username", None), patch("config.settings.myride_password", None):
        with pytest.raises(ValueError, match="No valid token, refresh token, or username/password credentials provided"):
            await auth.get_valid_access_token()
