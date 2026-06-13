import os
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Inject test environment variables before importing the FastAPI app
os.environ["GEMINI_API_KEY"] = "your_gemini_api_key_here"
os.environ["CHROMADB_PERSIST_DIRECTORY"] = "./vector-db/test_chroma_data"
os.environ["BACKEND_HOST"] = "127.0.0.1"
os.environ["BACKEND_PORT"] = "8000"

@pytest.fixture(autouse=True)
def mock_k8s_service(monkeypatch):
    """
    Automatically mock K8sService to isolate testing from live cluster connections.
    """
    mock_instance = MagicMock()
    
    mock_instance.get_pod_status.return_value = {
        "service": "payment-service",
        "pods": [
            {
                "name": "payment-service-5f9f8c6b9b-abc12",
                "status": "CrashLoopBackOff",
                "restart_count": 8,
                "ready": "0/1",
                "ip": "10.244.1.45",
                "node": "node-worker-1",
                "created_at": "2026-06-13T10:00:00Z"
            }
        ]
    }
    
    mock_instance.get_deployment_status.return_value = {
        "name": "payment-service",
        "replicas_desired": 3,
        "replicas_available": 2,
        "replicas_updated": 3,
        "strategy": "RollingUpdate"
    }
    
    mock_instance.get_pod_events.return_value = [
        {"type": "Warning", "reason": "BackOff", "message": "Back-off restarting failed container"}
    ]
    
    mock_instance.list_deployments.return_value = ["payment-service", "auth-service", "analytics-service", "frontend-service"]
    
    mock_instance.get_pod_logs.return_value = (
        "2026-06-13T12:00:45Z [ERROR] Failed to connect to database: Connection timeout after 30 seconds.\n"
    )
    
    # Apply monkeypatch to return the mock instance upon initialization
    monkeypatch.setattr("app.services.k8s_service.K8sService", lambda: mock_instance)
    monkeypatch.setattr("app.agents.sre_workflow.K8sService", lambda: mock_instance)
    return mock_instance

@pytest.fixture(autouse=True)
def mock_prometheus_service(monkeypatch):
    """
    Automatically mock PrometheusService to isolate testing from live HTTP requests.
    """
    mock_instance = MagicMock()
    
    mock_instance.get_all_metrics.return_value = {
        "cpu": {"metric": "cpu", "values": [{"timestamp": 1718280000, "value": 15.4}]},
        "memory": {"metric": "memory", "limit_mib": 512, "values": [{"timestamp": 1718280000, "value": 128.0}]},
        "latency": {"metric": "latency", "values": [{"timestamp": 1718280000, "value": 30000.0}]},
        "error_rate": {"metric": "error_rate", "values": [{"timestamp": 1718280000, "value": 100.0}]}
    }
    
    monkeypatch.setattr("app.services.prometheus_service.PrometheusService", lambda: mock_instance)
    monkeypatch.setattr("app.agents.sre_workflow.PrometheusService", lambda: mock_instance)
    return mock_instance

# Import app after environment is set up and services are patched
from app.main import app

@pytest.fixture(scope="session")
def test_client():
    """
    Session-wide fixture for the FastAPI test client.
    """
    with TestClient(app) as client:
        yield client
