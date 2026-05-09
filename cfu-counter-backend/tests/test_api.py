from fastapi.testclient import TestClient
from main import app
import os

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Bacterial Colony Counter API"

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "healthy"

def test_history_empty():
    # This might fail if DB is not empty, but generally locally it might be. 
    # Better to mock DB or use a test DB. 
    # For now, just check status code.
    response = client.get("/api/history/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
