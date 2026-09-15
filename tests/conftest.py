import pytest

@pytest.fixture
def user_info_fixture():
    return {
        "groups": [
            {
                "groupGuid": "9de7762a-ef18-45d7-a9a4-d3acc86501d1",
                "name": "QUAD VILLAGE TRANSPORTATION - ARDSLEY, NY",
                "proxyUrl": None
            }
        ],
        "userGuid": "b402f215-7cfa-44bb-a140-2eed977cf264",
        "name": "Andy Enkeboll",
        "firstName": "Andy",
        "lastName": "Enkeboll",
        "email": "andyenkeboll@gmail.com",
        "isBetaUser": False,
    }

@pytest.fixture
def student_info_fixture():
    return [
        {
            "studentId": 181166,
            "uniqueId": "001434589",
            "firstName": "SOREN",
            "lastName": "ENKEBOLL",
            "locationName": "CONCORD ROAD ELEMENTARY",
            "runInfo": [
                {
                    "runName": "ACR44 AM CRS MINI",
                    "visibleName": "ACR44 AM CRS MINI",
                    "rolloutBusNumber": "53",
                    "assetUniqueId": "53",
                }
            ]
        }
    ]

@pytest.fixture
def negotiate_fixture():
    return {
        "negotiateVersion": 1,
        "connectionId": "CUpxWFcR7Eul-ukQQLy4SA",
        "connectionToken": "sample_connection_token_12345",
        "availableTransports": [
            {"transport": "WebSockets", "transferFormats": ["Text", "Binary"]}
        ]
    }

@pytest.fixture
def ws_location_payload():
    return {
        "type": 1,
        "target": "NewLocation",
        "arguments": [
            {
                "assetId": 22,
                "assetUniqueId": "53",
                "logTime": "2026-09-02T12:28:30Z",
                "latitude": 41.0072594,
                "longitude": -73.8575439,
                "heading": 1,
                "speed": 17,
                "vendorId": None,
                "visibleRunName": None,
                "closestDirectionId": None,
                "distanceToClosestDirection": 0,
                "distanceToStartPoint": 0,
                "distanceToEndPoint": 0
            }
        ]
    }
