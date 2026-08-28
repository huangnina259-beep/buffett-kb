import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "src"))

from ai_gateway import (
    AnthropicAdapter,
    GenerationGateway,
    GenerationResult,
    GatewayError,
    ModelProfile,
    OpenAICompatibleAdapter,
    TaskRoute,
    parse_json_text,
)
from embedding_gateway import (
    EmbeddingError,
    EmbeddingGateway,
    EmbeddingProfile,
    OpenAIEmbeddingAdapter,
    load_embedding_profile,
)
import vector_store


class _GoodGenerationAdapter:
    def complete(self, profile, **kwargs):
        return GenerationResult("ok", profile.provider, profile.model)

    def stream(self, profile, **kwargs):
        yield "a"
        yield "b"


class _FailBeforeGenerationAdapter:
    def complete(self, profile, **kwargs):
        raise TimeoutError("temporary")

    def stream(self, profile, **kwargs):
        raise TimeoutError("temporary")
        yield  # pragma: no cover


class _FailAfterGenerationAdapter:
    def complete(self, profile, **kwargs):
        return GenerationResult("unused", profile.provider, profile.model)

    def stream(self, profile, **kwargs):
        yield "partial"
        raise TimeoutError("broken stream")


class _AuthError(RuntimeError):
    status_code = 401


class _AuthFailGenerationAdapter:
    def complete(self, profile, **kwargs):
        raise _AuthError("invalid secret")

    def stream(self, profile, **kwargs):
        raise _AuthError("invalid secret")
        yield  # pragma: no cover


class _FakeEmbeddingAdapter:
    def embed_documents(self, profile, texts):
        return [[float(len(text)), 1.0, 2.0] for text in texts]

    def embed_query(self, profile, text):
        return [float(len(text)), 1.0, 2.0]


class _BadDimensionEmbeddingAdapter:
    def embed_documents(self, profile, texts):
        return [[1.0, 2.0] for _ in texts]

    def embed_query(self, profile, text):
        return [1.0, 2.0]


class _FakeCollection:
    def __init__(self, count):
        self._count = count

    def count(self):
        return self._count


class _FakeOpenAIClient:
    last_init = None
    last_chat = None
    last_embedding = None

    def __init__(self, **kwargs):
        type(self).last_init = kwargs
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat_create))
        self.embeddings = SimpleNamespace(create=self._embedding_create)

    def _chat_create(self, **kwargs):
        type(self).last_chat = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="hello"))],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2),
        )

    def _embedding_create(self, **kwargs):
        type(self).last_embedding = kwargs
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=index, embedding=[float(index), 1.0, 2.0])
                for index, _ in enumerate(kwargs["input"])
            ]
        )


class _FakeAnthropicClient:
    last_call = None

    def __init__(self, **kwargs):
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        type(self).last_call = kwargs
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="hello")],
            usage=SimpleNamespace(input_tokens=4, output_tokens=2),
        )


class GenerationGatewayTests(unittest.TestCase):
    def _profile(self, name, provider):
        return ModelProfile(name=name, provider=provider, model=f"{name}-model")

    def test_complete_uses_fallback(self):
        gateway = GenerationGateway(
            profiles={
                "primary": self._profile("primary", "bad"),
                "backup": self._profile("backup", "good"),
            },
            routes={"task": TaskRoute("primary", ("backup",))},
            adapters={"bad": _FailBeforeGenerationAdapter, "good": _GoodGenerationAdapter},
        )
        result = gateway.complete("task", system="", messages=[], max_tokens=10)
        self.assertEqual(result.text, "ok")
        self.assertTrue(result.fallback_used)

    def test_stream_uses_fallback_only_before_output(self):
        gateway = GenerationGateway(
            profiles={
                "primary": self._profile("primary", "bad"),
                "backup": self._profile("backup", "good"),
            },
            routes={"task": TaskRoute("primary", ("backup",))},
            adapters={"bad": _FailBeforeGenerationAdapter, "good": _GoodGenerationAdapter},
        )
        self.assertEqual("".join(gateway.stream("task", system="", messages=[], max_tokens=10)), "ab")

    def test_stream_does_not_mix_models_after_output(self):
        gateway = GenerationGateway(
            profiles={
                "primary": self._profile("primary", "partial"),
                "backup": self._profile("backup", "good"),
            },
            routes={"task": TaskRoute("primary", ("backup",))},
            adapters={"partial": _FailAfterGenerationAdapter, "good": _GoodGenerationAdapter},
        )
        stream = gateway.stream("task", system="", messages=[], max_tokens=10)
        self.assertEqual(next(stream), "partial")
        with self.assertRaises(GatewayError):
            next(stream)

    def test_authentication_error_does_not_fallback(self):
        gateway = GenerationGateway(
            profiles={
                "primary": self._profile("primary", "auth"),
                "backup": self._profile("backup", "good"),
            },
            routes={"task": TaskRoute("primary", ("backup",))},
            adapters={"auth": _AuthFailGenerationAdapter, "good": _GoodGenerationAdapter},
        )
        with self.assertRaises(GatewayError) as raised:
            gateway.complete("task", system="", messages=[], max_tokens=10)
        self.assertNotIn("invalid secret", str(raised.exception))

    def test_json_fence_parser(self):
        self.assertEqual(parse_json_text('```json\n{"ok": true}\n```'), {"ok": True})

    def test_openai_compatible_adapter_contract(self):
        profile = ModelProfile(
            name="compatible",
            provider="openai_compatible",
            model="model-x",
            api_key_env="TEST_KEY",
            base_url="https://example.test/v1",
            supports_json_mode=True,
        )
        with patch.dict("os.environ", {"TEST_KEY": "secret"}, clear=True), patch(
            "openai.OpenAI", _FakeOpenAIClient
        ):
            result = OpenAICompatibleAdapter().complete(
                profile,
                system="system",
                messages=[{"role": "user", "content": "question"}],
                max_tokens=20,
                temperature=None,
                json_mode=True,
            )
        self.assertEqual(result.text, "hello")
        self.assertEqual(_FakeOpenAIClient.last_init["base_url"], "https://example.test/v1")
        self.assertEqual(_FakeOpenAIClient.last_chat["messages"][0]["role"], "system")
        self.assertEqual(_FakeOpenAIClient.last_chat["response_format"], {"type": "json_object"})

    def test_anthropic_adapter_contract(self):
        profile = ModelProfile(
            name="claude", provider="anthropic", model="model-y", api_key_env="TEST_KEY"
        )
        with patch.dict("os.environ", {"TEST_KEY": "secret"}, clear=True), patch(
            "anthropic.Anthropic", _FakeAnthropicClient
        ):
            result = AnthropicAdapter().complete(
                profile,
                system="system",
                messages=[{"role": "user", "content": "question"}],
                max_tokens=20,
                temperature=None,
                json_mode=False,
            )
        self.assertEqual(result.text, "hello")
        self.assertEqual(_FakeAnthropicClient.last_call["system"], "system")


class EmbeddingGatewayTests(unittest.TestCase):
    def test_openai_compatible_embedding_contract(self):
        profile = EmbeddingProfile(
            name="compatible",
            provider="openai_compatible",
            model="embed-x",
            api_key_env="TEST_KEY",
            base_url="https://example.test/v1",
            dimension=3,
        )
        with patch.dict("os.environ", {"TEST_KEY": "secret"}, clear=True), patch(
            "openai.OpenAI", _FakeOpenAIClient
        ):
            vectors = OpenAIEmbeddingAdapter().embed_documents(profile, ["a", "b"])
        self.assertEqual(len(vectors), 2)
        self.assertEqual(_FakeOpenAIClient.last_embedding["model"], "embed-x")
        self.assertNotIn("dimensions", _FakeOpenAIClient.last_embedding)

    def test_official_openai_can_request_shortened_dimensions(self):
        profile = EmbeddingProfile(
            name="openai",
            provider="openai",
            model="text-embedding-3-small",
            api_key_env="TEST_KEY",
            dimension=3,
            request_dimensions=True,
        )
        with patch.dict("os.environ", {"TEST_KEY": "secret"}, clear=True), patch(
            "openai.OpenAI", _FakeOpenAIClient
        ):
            OpenAIEmbeddingAdapter().embed_query(profile, "test")
        self.assertEqual(_FakeOpenAIClient.last_embedding["dimensions"], 3)

    def test_selects_active_profile_from_multiple_suppliers(self):
        profiles = {
            "vendor_a": {"provider": "openai", "model": "embed-a", "api_key_env": "KEY_A"},
            "vendor_b": {
                "provider": "openai_compatible",
                "model": "embed-b",
                "api_key_env": "KEY_B",
                "base_url": "https://example.test/v1",
            },
        }
        with patch("ai_settings.load_saved_settings", return_value=None), patch.dict(
            "os.environ",
            {
                "EMBEDDING_PROFILES_JSON": json.dumps(profiles),
                "EMBEDDING_ACTIVE_PROFILE": "vendor_b",
            },
            clear=True,
        ):
            profile = load_embedding_profile()
        self.assertEqual(profile.name, "vendor_b")
        self.assertEqual(profile.model, "embed-b")

    def test_batches_and_validates_vectors(self):
        profile = EmbeddingProfile(
            name="test", provider="fake", model="embed", dimension=3, batch_size=2
        )
        gateway = EmbeddingGateway(profile, adapters={"fake": _FakeEmbeddingAdapter})
        vectors = gateway.embed_documents(["a", "bb", "ccc"])
        self.assertEqual(len(vectors), 3)
        self.assertEqual(gateway.embed_query("abcd")[0], 4.0)

    def test_rejects_dimension_mismatch(self):
        profile = EmbeddingProfile(name="test", provider="bad", model="embed", dimension=3)
        gateway = EmbeddingGateway(profile, adapters={"bad": _BadDimensionEmbeddingAdapter})
        with self.assertRaises(EmbeddingError):
            gateway.embed_query("query")

    def test_manifest_prevents_cross_model_queries(self):
        profile = EmbeddingProfile(name="new", provider="fake", model="new-model", dimension=3)
        gateway = EmbeddingGateway(profile, adapters={"fake": _FakeEmbeddingAdapter})
        with tempfile.TemporaryDirectory() as temp_dir:
            old_db_dir = vector_store.DB_DIR
            vector_store.DB_DIR = Path(temp_dir)
            try:
                path = vector_store.manifest_path()
                path.write_text(
                    json.dumps({"provider": "fake", "model": "old-model", "dimension": 3}),
                    encoding="utf-8",
                )
                with self.assertRaises(Exception) as raised:
                    vector_store.ensure_index_compatible(_FakeCollection(10), gateway)
                self.assertIn("does not match", str(raised.exception))
            finally:
                vector_store.DB_DIR = old_db_dir

    def test_legacy_index_requires_explicit_local_profile(self):
        cloud = EmbeddingGateway(
            EmbeddingProfile(name="cloud", provider="fake", model="cloud", dimension=3),
            adapters={"fake": _FakeEmbeddingAdapter},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            old_db_dir = vector_store.DB_DIR
            vector_store.DB_DIR = Path(temp_dir)
            try:
                with self.assertRaises(Exception) as raised:
                    vector_store.ensure_index_compatible(_FakeCollection(10), cloud)
                self.assertIn("no embedding manifest", str(raised.exception))
            finally:
                vector_store.DB_DIR = old_db_dir


if __name__ == "__main__":
    unittest.main()
