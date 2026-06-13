import os
import pytest
from fastapi.testclient import TestClient

# Inject test environment variables before importing the FastAPI app
os.environ["GEMINI_API_KEY"] = "your_gemini_api_key_here"
os.environ["CHROMADB_PERSIST_DIRECTORY"] = "./vector-db/test_chroma_data"
os.environ["BACKEND_HOST"] = "127.0.0.1"
os.environ["BACKEND_PORT"] = "8000"
os.environ["MOCK_MODE"] = "True"

# Import app after environment is set up
from app.main import app

@pytest.fixture(scope="session")
def test_client():
    """
    Session-wide fixture for the FastAPI test client.
    """
    with TestClient(app) as client:
        yield client
