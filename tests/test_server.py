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
            "raw_result_count": 3,
            "filtered_count": 1,
            "filter_stats": {"wanted_post": 1},
            "products": [
                {"title": "光威 DDR5 6000 32G", "price": 2000.0, "source_platform": "xianyu"},
                {"title": "金士顿 DDR5 6000 32G", "price": 2500.0, "source_platform": "xianyu"},
            ],
            "sample_count": 2,
        }

    async def validate_state(self, strategy, account_state_file):
        if account_state_file == "expired.json":
            raise LoginRequiredError("login required")
        return {
            "valid": True,
            "state_file": account_state_file or "goofish_state.json",
            "keyword": "电脑 内存",
            "sample_count": 1,
            "page_url": "https://www.goofish.com/search?q=电脑+内存",
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
            validation_keyword="电脑 内存",
        )

    def test_search_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(self.build_config(tmpdir), search_service=StubSearchService())
            client = TestClient(app)
            response = client.post("/api/v1/search", json={"keyword": "DDR5 6000 32G", "category": "RAM"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["sample_count"], 2)
            self.assertEqual(response.json()["filtered_count"], 1)
            self.assertEqual(response.json()["filter_stats"]["wanted_post"], 1)
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

    def test_promote_login_state_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = self.build_config(tmpdir)
            app = create_app(cfg, search_service=StubSearchService())
            client = TestClient(app)
            client.post("/api/v1/login-state", json={"content": "{\"cookies\": []}", "file_name": "acc_1.json"})
            response = client.post("/api/v1/login-state/default", json={"file_name": "acc_1.json"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["item"]["name"], "goofish_state.json")

    def test_validate_state_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(self.build_config(tmpdir), search_service=StubSearchService())
            client = TestClient(app)
            response = client.post("/api/v1/validate-state", json={"account_state_file": "acc_1.json"})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["valid"])

    def test_validate_state_maps_login_error_to_401(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app = create_app(self.build_config(tmpdir), search_service=StubSearchService())
            client = TestClient(app)
            response = client.post("/api/v1/validate-state", json={"account_state_file": "expired.json"})
            self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
