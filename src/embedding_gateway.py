"""Provider-neutral text embedding gateway.

Cloud embeddings are the production default. Local Sentence Transformers are
available only when ``EMBEDDING_PROVIDER=local`` is explicitly configured.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Protocol, Sequence


class EmbeddingError(RuntimeError):
    """Base embedding error."""


class EmbeddingConfigError(EmbeddingError):
    """Embedding configuration is missing or incompatible."""


@dataclass(frozen=True)
class EmbeddingProfile:
    name: str
    provider: str
    model: str
    api_key_env: str = ""
    api_key_value: str = ""
    base_url: str | None = None
    dimension: int | None = None
    request_dimensions: bool = False
    batch_size: int = 64
    timeout: float = 60.0
    max_retries: int = 3

    @property
    def api_key(self) -> str:
        if self.api_key_value:
            return self.api_key_value
        return os.environ.get(self.api_key_env, "") if self.api_key_env else ""

    def public_dict(self) -> dict:
        return {
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "dimension": self.dimension,
            "batch_size": self.batch_size,
        }


class EmbeddingAdapter(Protocol):
    def embed_documents(self, profile: EmbeddingProfile, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, profile: EmbeddingProfile, text: str) -> list[float]: ...


def _require_api_key(profile: EmbeddingProfile) -> str:
    key = profile.api_key
    if not key:
        env_name = profile.api_key_env or "the configured API key variable"
        raise EmbeddingConfigError(
            f"Embedding profile '{profile.name}' requires {env_name}. "
            "Cloud embeddings are the default; set EMBEDDING_PROVIDER=local only for explicit offline use."
        )
    return key


class OpenAIEmbeddingAdapter:
    """OpenAI and services implementing the compatible /embeddings API."""

    def _client(self, profile: EmbeddingProfile):
        from openai import OpenAI

        kwargs = {
            "api_key": _require_api_key(profile),
            "timeout": profile.timeout,
            "max_retries": profile.max_retries,
        }
        if profile.base_url:
            kwargs["base_url"] = profile.base_url
        return OpenAI(**kwargs)

    def _embed(self, profile: EmbeddingProfile, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        kwargs = {"model": profile.model, "input": list(texts)}
        # ``dimension`` is normally the observed/expected vector size. Sending
        # it as a request parameter is a separate capability supported by
        # Matryoshka models only, so compatible providers must opt in.
        if profile.dimension and profile.request_dimensions:
            kwargs["dimensions"] = profile.dimension
        response = self._client(profile).embeddings.create(**kwargs)
        ordered = sorted(response.data, key=lambda item: item.index)
        return [list(item.embedding) for item in ordered]

    def embed_documents(self, profile: EmbeddingProfile, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(profile, texts)

    def embed_query(self, profile: EmbeddingProfile, text: str) -> list[float]:
        vectors = self._embed(profile, [text])
        return vectors[0]


class LocalSentenceTransformerAdapter:
    """Optional offline adapter; imported lazily so cloud installs stay light."""

    _models: dict[str, object] = {}

    def _model(self, profile: EmbeddingProfile):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingConfigError(
                "Local embeddings require requirements-local.txt. "
                "Install it explicitly or configure a cloud embedding provider."
            ) from exc
        if profile.model not in self._models:
            allow_download = os.environ.get("LOCAL_EMBEDDING_ALLOW_DOWNLOAD", "false").lower() in {
                "1", "true", "yes", "on"
            }
            self._models[profile.model] = SentenceTransformer(
                profile.model,
                local_files_only=not allow_download,
            )
        return self._models[profile.model]

    def _embed(self, profile: EmbeddingProfile, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._model(profile).encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    def embed_documents(self, profile: EmbeddingProfile, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(profile, texts)

    def embed_query(self, profile: EmbeddingProfile, text: str) -> list[float]:
        return self._embed(profile, [text])[0]


EmbeddingAdapterFactory = Callable[[], EmbeddingAdapter]


def _profile_from_simple_env() -> EmbeddingProfile:
    provider = os.environ.get("EMBEDDING_PROVIDER", "openai").strip().lower()
    if provider == "local":
        default_model = "sentence-transformers/all-MiniLM-L6-v2"
        default_key_env = ""
        default_dimension = 384
    else:
        default_model = "text-embedding-3-small" if provider == "openai" else ""
        default_key_env = {
            "openai": "OPENAI_API_KEY",
            "openai_compatible": "EMBEDDING_API_KEY",
        }.get(provider, "EMBEDDING_API_KEY")
        default_dimension = None

    model = os.environ.get("EMBEDDING_MODEL", default_model).strip()
    if not model:
        raise EmbeddingConfigError("EMBEDDING_MODEL must be configured.")
    dimension_raw = os.environ.get("EMBEDDING_DIMENSION", "").strip()
    dimension = int(dimension_raw) if dimension_raw else default_dimension
    return EmbeddingProfile(
        name=os.environ.get("EMBEDDING_PROFILE", "knowledge_base_default"),
        provider=provider,
        model=model,
        api_key_env=os.environ.get("EMBEDDING_API_KEY_ENV", default_key_env),
        base_url=os.environ.get("EMBEDDING_BASE_URL") or None,
        dimension=dimension,
        request_dimensions=(
            provider == "openai"
            and os.environ.get("EMBEDDING_REQUEST_DIMENSIONS", "true").lower()
            in {"1", "true", "yes", "on"}
        ),
        batch_size=max(1, int(os.environ.get("EMBEDDING_BATCH_SIZE", "64"))),
        timeout=float(os.environ.get("EMBEDDING_TIMEOUT", "60")),
        max_retries=max(0, int(os.environ.get("EMBEDDING_MAX_RETRIES", "3"))),
    )


def load_embedding_profiles() -> dict[str, EmbeddingProfile]:
    from ai_settings import find_profile, load_saved_settings

    saved = load_saved_settings()
    if saved:
        active = saved["routes"].get("embedding")
        if not active:
            raise EmbeddingConfigError("页面模型配置尚未选择向量模型。")
        provider, model = find_profile(saved, active)
        provider_type = provider["provider"]
        if provider_type in {"anthropic"}:
            raise EmbeddingConfigError("Anthropic 供应商不支持 OpenAI 兼容向量接口。")
        profile = EmbeddingProfile(
            name=active,
            provider="openai" if provider_type == "openai" else "openai_compatible",
            model=model["id"],
            api_key_value=provider.get("api_key", ""),
            base_url=provider.get("base_url") or None,
            dimension=model.get("dimension"),
            request_dimensions=False,
        )
        return {active: profile}

    raw_json = os.environ.get("EMBEDDING_PROFILES_JSON", "").strip()
    if not raw_json:
        profile = _profile_from_simple_env()
        return {profile.name: profile}
    try:
        raw_profiles = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise EmbeddingConfigError(f"EMBEDDING_PROFILES_JSON is not valid JSON: {exc}") from exc
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise EmbeddingConfigError("EMBEDDING_PROFILES_JSON must be a non-empty JSON object.")

    profiles: dict[str, EmbeddingProfile] = {}
    for name, raw in raw_profiles.items():
        if not isinstance(raw, dict):
            raise EmbeddingConfigError(f"Embedding profile '{name}' must be an object.")
        provider = str(raw.get("provider", "openai_compatible")).lower()
        model = str(raw.get("model", "")).strip()
        if not model:
            raise EmbeddingConfigError(f"Embedding profile '{name}' has no model ID.")
        default_key_env = "OPENAI_API_KEY" if provider == "openai" else "EMBEDDING_API_KEY"
        dimension = raw.get("dimension")
        profiles[name] = EmbeddingProfile(
            name=name,
            provider=provider,
            model=model,
            api_key_env=str(raw.get("api_key_env", default_key_env)),
            base_url=raw.get("base_url"),
            dimension=int(dimension) if dimension is not None else None,
            request_dimensions=bool(raw.get("request_dimensions", provider == "openai")),
            batch_size=max(1, int(raw.get("batch_size", 64))),
            timeout=float(raw.get("timeout", 60)),
            max_retries=max(0, int(raw.get("max_retries", 3))),
        )
    return profiles


def load_embedding_profile() -> EmbeddingProfile:
    profiles = load_embedding_profiles()
    try:
        from ai_settings import load_saved_settings

        if load_saved_settings():
            return next(iter(profiles.values()))
    except ValueError as exc:
        raise EmbeddingConfigError(str(exc)) from exc
    active = os.environ.get("EMBEDDING_ACTIVE_PROFILE") or os.environ.get("EMBEDDING_PROFILE")
    if active:
        profile = profiles.get(active)
        if not profile:
            raise EmbeddingConfigError(
                f"Active embedding profile '{active}' is not present in EMBEDDING_PROFILES_JSON."
            )
        return profile
    if len(profiles) > 1:
        raise EmbeddingConfigError(
            "EMBEDDING_ACTIVE_PROFILE is required when multiple embedding profiles are configured."
        )
    return next(iter(profiles.values()))


class EmbeddingGateway:
    def __init__(
        self,
        profile: EmbeddingProfile | None = None,
        adapters: dict[str, EmbeddingAdapterFactory] | None = None,
    ) -> None:
        self.profile = profile or load_embedding_profile()
        self.adapters = adapters or {
            "openai": OpenAIEmbeddingAdapter,
            "openai_compatible": OpenAIEmbeddingAdapter,
            "local": LocalSentenceTransformerAdapter,
        }
        self._adapter_instance: EmbeddingAdapter | None = None
        self._observed_dimension: int | None = None

    def _adapter(self) -> EmbeddingAdapter:
        factory = self.adapters.get(self.profile.provider)
        if not factory:
            raise EmbeddingConfigError(
                f"Unsupported embedding provider '{self.profile.provider}'. "
                "Use openai, openai_compatible, local, or register an adapter."
            )
        if self._adapter_instance is None:
            self._adapter_instance = factory()
        return self._adapter_instance

    def _validate(self, vectors: list[list[float]], expected_count: int) -> list[list[float]]:
        if len(vectors) != expected_count:
            raise EmbeddingError(
                f"Embedding provider returned {len(vectors)} vectors for {expected_count} inputs."
            )
        if not vectors:
            return vectors
        dimension = len(vectors[0])
        if dimension == 0 or any(len(vector) != dimension for vector in vectors):
            raise EmbeddingError("Embedding provider returned inconsistent vector dimensions.")
        if self.profile.dimension and dimension != self.profile.dimension:
            raise EmbeddingError(
                f"Embedding dimension mismatch: configured {self.profile.dimension}, received {dimension}."
            )
        if self._observed_dimension and dimension != self._observed_dimension:
            raise EmbeddingError(
                f"Embedding dimension changed during this process: {self._observed_dimension} -> {dimension}."
            )
        self._observed_dimension = dimension
        return vectors

    @property
    def dimension(self) -> int | None:
        return self.profile.dimension or self._observed_dimension

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        all_vectors: list[list[float]] = []
        batch_size = self.profile.batch_size
        for start in range(0, len(texts), batch_size):
            batch = list(texts[start:start + batch_size])
            try:
                vectors = self._adapter().embed_documents(self.profile, batch)
            except EmbeddingConfigError:
                raise
            except Exception as exc:
                logging.warning(
                    "[Embedding] profile=%s document batch failed: %s",
                    self.profile.name,
                    exc,
                )
                raise EmbeddingError(
                    f"Embedding request failed for profile '{self.profile.name}'. Check server logs."
                ) from exc
            all_vectors.extend(self._validate(vectors, len(batch)))
        return all_vectors

    def embed_query(self, text: str) -> list[float]:
        try:
            vector = self._adapter().embed_query(self.profile, text)
        except EmbeddingConfigError:
            raise
        except Exception as exc:
            logging.warning(
                "[Embedding] profile=%s query failed: %s", self.profile.name, exc
            )
            raise EmbeddingError(
                f"Embedding request failed for profile '{self.profile.name}'. Check server logs."
            ) from exc
        return self._validate([vector], 1)[0]

    def status(self) -> dict:
        return {
            **self.profile.public_dict(),
            "configured": self.profile.provider == "local" or bool(self.profile.api_key),
            "local_inference": self.profile.provider == "local",
        }


@lru_cache(maxsize=1)
def get_embedding_gateway() -> EmbeddingGateway:
    return EmbeddingGateway()


def reset_embedding_gateway() -> None:
    get_embedding_gateway.cache_clear()
