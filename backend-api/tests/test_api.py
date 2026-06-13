import pytest

def test_health_endpoint(test_client):
    """
    Test GET /health returns operational status.
    """
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Healthy"
    assert "chromadb" in data
    assert "api_key_configured" in data


def test_deployments_endpoint(test_client):
    """
    Test GET /deployments returns a list of deployments.
    """
    response = test_client.get("/deployments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "payment-service" in data



def test_logs_endpoint(test_client):
    """
    Test GET /logs/{service_name} returns mock logs.
    """
    response = test_client.get("/logs/payment-service")
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == "payment-service"
    assert "Failed to connect to database" in data["logs"]


def test_diagnose_endpoint(test_client):
    """
    Test POST /diagnose performs log and metrics SRE pipeline runs.
    """
    payload = {"service_name": "payment-service"}
    response = test_client.post("/diagnose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == "payment-service"
    assert "pod_status" in data
    assert "log_analysis" in data
    assert "metrics_analysis" in data
    assert "root_cause" in data
    assert "recommendations" in data
    assert data["confidence_score"] > 0.0


def test_explain_error_endpoint(test_client):
    """
    Test POST /explain-error gives diagnostic descriptions.
    """
    payload = {"error_message": "dial tcp 10.244.1.45:5432: connect: connection refused"}
    response = test_client.post("/explain-error", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert len(data["potential_causes"]) > 0
    assert len(data["remediation_steps"]) > 0


def test_search_docs_endpoint(test_client):
    """
    Test POST /search-docs accesses ChromaDB indexing.
    """
    payload = {"query": "database connection timeout", "limit": 2}
    response = test_client.post("/search-docs", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    # Results can be empty if seeding hasn't completed or in tests, but schema must match
    results = data["results"]
    if results:
        assert "content" in results[0]
        assert "metadata" in results[0]


def test_ask_endpoint(test_client):
    """
    Test POST /ask retrieves structured responses.
    """
    payload = {"question": "How do I troubleshoot an OOMKilled container?"}
    response = test_client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
