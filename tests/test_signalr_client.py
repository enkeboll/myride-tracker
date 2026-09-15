import pytest
import json
from unittest.mock import AsyncMock
from signalr_client import SignalRClient, RECORD_SEPARATOR

def test_build_ws_url():
    client = SignalRClient(
        tenant_id="tenant_abc",
        connection_token="conn_token_123",
        access_token="access_tok_456"
    )
    url = client.build_ws_url()
    assert "x-tenant-id=tenant_abc" in url
    assert "id=conn_token_123" in url
    assert "access_token=access_tok_456" in url
    assert url.startswith("wss://myridek12.tylerapi.com/livevehiclehub")

@pytest.mark.asyncio
async def test_handle_record_location_callback(ws_location_payload):
    received_location = []

    async def mock_callback(data, raw_str):
        received_location.append((data, raw_str))

    client = SignalRClient(
        tenant_id="tenant_abc",
        connection_token="conn_token_123",
        access_token="access_tok_456",
        on_location=mock_callback
    )

    record_str = json.dumps(ws_location_payload)
    await client._handle_record(record_str)

    assert len(received_location) == 1
    loc_data, raw = received_location[0]
    assert loc_data["assetUniqueId"] == "53"
    assert loc_data["latitude"] == 41.0072594
    assert loc_data["longitude"] == -73.8575439
    assert loc_data["speed"] == 17
