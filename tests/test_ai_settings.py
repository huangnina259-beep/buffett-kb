import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient

import ai_settings
from ai_gateway import load_profiles, load_task_routes
from embedding_gateway import load_embedding_profile
from reranker_gateway import RerankerGateway, RerankerProfile
import server


class AISettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path_patch = patch.object(
            ai_settings, "SETTINGS_PATH", Path(self.temp.name) / "ai_settings.json"
        )
        self.path_patch.start()

    def tearDown(self):
        self.path_patch.stop()
        self.temp.cleanup()

    def test_default_contains_requested_wtsht_models(self):
        public = ai_settings.public_settings()
        provider = public["providers"][0]
        self.assertEqual(provider["base_url"], "https://openapi.wtsht.cn/v1")
        self.assertEqual(
            [model["id"] for model in provider["models"]],
            [
                "DeepSeek-V4-Flash-YR",
                "Qwen3-Embedding-8B",
                "Qwen3-Reranker-0.6B",
                "Qwen3.8-27b",
            ],
        )
        self.assertNotIn("api_key", provider)
        self.assertFalse(provider["has_api_key"])

    def test_secret_is_redacted_and_blank_update_preserves_it(self):
        settings = ai_settings.default_settings()
        settings["providers"][0]["api_key"] = "top-secret"
        saved = ai_settings.save_settings(settings)
        self.assertEqual(saved["providers"][0]["api_key"], "top-secret")
        public = ai_settings.public_settings(saved)
        self.assertNotIn("api_key", public["providers"][0])
        self.assertTrue(public["providers"][0]["has_api_key"])

        update = ai_settings.default_settings()
        update["providers"][0]["api_key"] = ""
        ai_settings.save_settings(update)
        self.assertEqual(
            ai_settings.load_saved_settings()["providers"][0]["api_key"],
            "top-secret",
        )

    def test_saved_settings_feed_all_runtime_gateways(self):
        settings = ai_settings.default_settings()
        settings["providers"][0]["api_key"] = "secret"
        ai_settings.save_settings(settings)

        profiles = load_profiles()
        routes = load_task_routes(profiles)
        generation = profiles[routes["knowledge_answer"].primary]
        embedding = load_embedding_profile()
        self.assertEqual(generation.model, "DeepSeek-V4-Flash-YR")
        self.assertEqual(generation.api_key, "secret")
        self.assertEqual(embedding.model, "Qwen3-Embedding-8B")
        self.assertEqual(embedding.api_key, "secret")

    def test_api_never_returns_secret(self):
        settings = ai_settings.default_settings()
        settings["providers"][0]["api_key"] = "api-secret"
        client = TestClient(server.app)
        response = client.put(
            "/api/ai/settings",
            json={"providers": settings["providers"], "routes": settings["routes"]},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("api-secret", response.text)
        self.assertTrue(body["settings"]["providers"][0]["has_api_key"])
        fetched = client.get("/api/ai/settings")
        self.assertNotIn("api-secret", fetched.text)

    def test_connection_test_requires_key(self):
        client = TestClient(server.app)
        response = client.post(
            "/api/ai/test",
            json={
                "provider_id": "wtsht",
                "provider": "openai_compatible",
                "base_url": "https://openapi.wtsht.cn/v1",
                "model": "DeepSeek-V4-Flash-YR",
                "capability": "generation",
                "api_key": "",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("API Key", response.json()["detail"])


class RerankerGatewayTests(unittest.TestCase):
    def test_openai_compatible_reranker_contract(self):
        profile = RerankerProfile(
            name="test",
            provider="openai_compatible",
            model="rerank-x",
            base_url="https://example.test/v1",
            api_key="secret",
        )
        response = SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"results": [{"index": 1, "relevance_score": 0.9}]},
        )
        with patch("httpx.post", return_value=response) as request:
            ranked = RerankerGateway(profile).rerank("query", ["a", "b"], 2)
        self.assertEqual(ranked[0].index, 1)
        self.assertEqual(request.call_args.args[0], "https://example.test/v1/rerank")
        self.assertEqual(request.call_args.kwargs["json"]["model"], "rerank-x")
        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer secret")


if __name__ == "__main__":
    unittest.main()
