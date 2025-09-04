import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """
    Creates a FastAPI TestClient fixture for the entire test session.
    This client can be used to make HTTP requests to the application.
    """
    client = TestClient(app)
    yield client
