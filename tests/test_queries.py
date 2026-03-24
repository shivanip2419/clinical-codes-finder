from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_find_codes_shape():
    response = client.post("/find-codes", json={"query": "diabetes", "max_per_system": 3})
    assert response.status_code == 200
    payload = response.json()
    assert "results_by_system" in payload
    assert "summary" in payload
    assert "trace" in payload
