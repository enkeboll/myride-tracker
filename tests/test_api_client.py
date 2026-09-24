from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from lib.api_client import MyRideAPIClient


@pytest.mark.asyncio
async def test_get_user_info(user_info_fixture):
    client = MyRideAPIClient()

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = user_info_fixture

    mock_session = MagicMock(spec=aiohttp.ClientSession)
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    data = await client.get_user_info("fake_token", session=mock_session)
    assert data["userGuid"] == "b402f215-7cfa-44bb-a140-2eed977cf264"
    assert data["groups"][0]["groupGuid"] == "9de7762a-ef18-45d7-a9a4-d3acc86501d1"


@pytest.mark.asyncio
async def test_get_student_info(student_info_fixture):
    client = MyRideAPIClient()

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = student_info_fixture

    mock_session = MagicMock(spec=aiohttp.ClientSession)
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    data = await client.get_student_info("fake_token", "tenant_123", session=mock_session)
    assert len(data) == 1
    assert data[0]["firstName"] == "SOREN"
    assert data[0]["runInfo"][0]["assetUniqueId"] == "53"


@pytest.mark.asyncio
async def test_negotiate_signalr(negotiate_fixture):
    client = MyRideAPIClient()

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json.return_value = negotiate_fixture

    mock_session = MagicMock(spec=aiohttp.ClientSession)
    mock_session.post.return_value.__aenter__.return_value = mock_resp

    data = await client.negotiate_signalr("fake_token", "tenant_123", session=mock_session)
    assert data["connectionToken"] == "sample_connection_token_12345"
