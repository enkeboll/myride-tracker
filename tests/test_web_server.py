import pytest
from aiohttp.test_utils import TestClient, TestServer
from web.server import create_web_app
from lib.db import init_db

@pytest.mark.asyncio
async def test_web_app_index_and_api():
    await init_db()
    app = create_web_app()
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        # Test index route
        resp = await client.get("/")
        assert resp.status == 200

        # Test API status endpoint
        resp_status = await client.get("/api/status")
        assert resp_status.status == 200
        data_status = await resp_status.json()
        assert "is_active_window" in data_status
        assert "status_message" in data_status

        # Test API locations endpoint
        resp_locs = await client.get("/api/locations?limit=10")
        assert resp_locs.status == 200
        data_locs = await resp_locs.json()
        assert isinstance(data_locs, list)

        # Test API stats endpoint
        resp_stats = await client.get("/api/stats")
        assert resp_stats.status == 200
        data_stats = await resp_stats.json()
        assert "total_points" in data_stats
    finally:
        await client.close()
