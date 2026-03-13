import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Config
from app.server import create_app
from app.services.search_service import LoginRequiredError


class StubSearchService:
    async def search(self, keyword, category, limit, strategy, account_state_file):
        if keyword == "login-error":
            raise LoginRequiredError("login required")
        return {
            "keyword": keyword,
            "category": category,
            "limit": limit,
            "state_file": "acc_1.json",
            "products": [
                {"title": "光威 DDR5 6000 32G", "price": 2000.0},
                {"title": "金士顿 DDR5 6000 32G", "price": 2500.0},
            ],
            "sample_count": 2,
        }


class StubPersistenceService:
    def persist_search_result(self, payload, summary=None):
        class Result:
            job_id = "job-1"
            persisted_count = len(payload.get("products", []))
        return Result()


class ServerTest(unittest.TestCase):
    def build_config(self, tmpdir: str) -> Config:
        state_dir = Path(tmpdir) / "state"
        return Config(
            service_name="rigel-goofish-collector",
            http_port=8080,
            mode="market_reference",
            state_dir=state_dir,
            root_state_file=state_dir / "goofish_state.json",
            upstream_enabled=True,
            run_headless=True,
            search_timeout_ms=1000,
            browser_channel="chromium",
            postgres_dsn=None,
        )

    def test_search_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(self.build_config(tmpdir), search_service=StubSearchService())
            client = TestClient(app)
            response = client.post("/api/v1/search", json={"keyword": "DDR5 6000 32G", "category": "RAM"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["sample_count"], 2)
            self.assertFalse(response.json()["persisted"])

    def test_market_summary_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(self.build_config(tmpdir), search_service=StubSearchService())
            client = TestClient(app)
            response = client.post("/api/v1/market/summary", json={"keyword": "DDR5 6000 32G", "category": "RAM"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["summary"]["avg_price"], 2250.0)

    def test_login_error_maps_to_401(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(self.build_config(tmpdir), search_service=StubSearchService())
            client = TestClient(app)
            response = client.post("/api/v1/search", json={"keyword": "login-error"})
            self.assertEqual(response.status_code, 401)

    def test_persisted_search_returns_job_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(
                self.build_config(tmpdir),
                search_service=StubSearchService(),
                persistence_service=StubPersistenceService(),
            )
            client = TestClient(app)
            response = client.post("/api/v1/search", json={"keyword": "DDR5 6000 32G", "category": "RAM", "persist": True})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["persisted"])
            self.assertEqual(response.json()["job_id"], "job-1")
            self.assertEqual(response.json()["persisted_count"], 2)


if __name__ == "__main__":
    unittest.main()
