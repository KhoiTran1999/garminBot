import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    print("[PASS] Health check endpoint passed:", data["status"])

def test_auth_me_unauthorized():
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    print("[PASS] Unauthorized check passed (returned 401 as expected)")

def test_login_invalid():
    response = client.post("/api/auth/login", json={"email": "nonexistent@test.com", "password": "wrong"})
    assert response.status_code == 401
    print("[PASS] Invalid login check passed (returned 401 as expected)")

if __name__ == "__main__":
    test_health()
    test_auth_me_unauthorized()
    test_login_invalid()
    print("[SUCCESS] All API integration smoke tests PASSED!")
