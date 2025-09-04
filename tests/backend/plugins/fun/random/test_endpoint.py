import os

from fastapi.testclient import TestClient

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError(
        "API_KEY environment variable not set for tests. Check .env.test file."
    )

HEADERS = {"X-API-Key": API_KEY}


def test_roll_dice_endpoint(test_client: TestClient):
    response = test_client.get("/fun/random/roll", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    assert isinstance(data["result"], int)
    assert 1 <= data["result"] <= 6


def test_make_choice_endpoint(test_client: TestClient):
    params = {"options": "apple;banana;cherry"}
    response = test_client.get("/fun/random/choice", headers=HEADERS, params=params)
    assert response.status_code == 200
    data = response.json()
    assert "choice" in data
    assert data["choice"] in ["apple", "banana", "cherry"]


def test_make_choice_endpoint_bad_request(test_client: TestClient):
    response = test_client.get("/fun/random/choice", headers=HEADERS)
    assert response.status_code == 422
