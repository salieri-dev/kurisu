# tests/backend/conftest.py

import pytest
from fastapi.testclient import TestClient

from backend.main import app  # Import your main FastAPI app instance


@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """
    Creates a FastAPI TestClient fixture for the entire test session.
    This client can be used to make HTTP requests to the application.
    """
    client = TestClient(app)
    yield client
    # You can add cleanup code here if needed, e.g., client.close()
