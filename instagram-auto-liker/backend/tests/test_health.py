import os

os.environ.setdefault("MASTER_KEY", "test-master-key-12345")
os.environ.setdefault("ADMIN_PASSWORD", "x")
os.environ.setdefault("JWT_SECRET", "x")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_health():
    with TestClient(app) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
