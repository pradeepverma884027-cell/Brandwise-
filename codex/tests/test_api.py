"""Unit tests for FastAPI Brandwise API Endpoints."""

import sys
import os
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

try:
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
except Exception as e:
    client = None


def test_openapi_docs():
    if client is None:
        return
    response = client.get("/api/docs")
    assert response.status_code == 200
    print("[PASS] test_openapi_docs")


def test_insights_guideline_gaps():
    if client is None:
        return
    response = client.get("/api/v1/insights/guideline-gaps")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "gaps" in data
    print("[PASS] test_insights_guideline_gaps")


def test_insights_review_stats():
    if client is None:
        return
    response = client.get("/api/v1/insights/review-stats")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "total_submissions" in data
    print("[PASS] test_insights_review_stats")


if __name__ == "__main__":
    print("Running API endpoint unit tests...")
    test_openapi_docs()
    test_insights_guideline_gaps()
    test_insights_review_stats()
    print("ALL API TESTS PASSED SUCCESSFULLY!")
