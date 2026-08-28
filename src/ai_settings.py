"""Persistent, UI-managed AI provider configuration.

Secrets are stored only in the backend runtime data directory. Public payloads
contain a boolean indicating whether a key exists, never the key itself.
Environment-based configuration remains available until the first UI settings
save, which makes upgrading an existing installation non-disruptive.
"""
from __future__ import annotations

import json
import re
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT_DIR / "database" / "ai_settings.json"
_LOCK = threading.RLock()

GENERATION_TASKS = (
    "knowledge_answer",
    "tutor_dialogue",
    "coach_dialogue",
    "structured_feedback",
    "long_synthesis",
    "daily_digest",
)
CAPABILITIES = {"generation", "embedding", "reranker"}
PROVIDER_TYPES = {"openai_compatible", "openai", "anthropic", "gemini"}


def _profile_id(provider_id: str, model_id: str) -> str:
    return f"{provider_id}::{model_id}"


def default_settings() -> dict[str, Any]:
    """Return the editable WTSHT starter configuration requested by the user."""
    provider_id = "wtsht"
    generation = _profile_id(provider_id, "DeepSeek-V4-Flash-YR")
    return {
        "version": 1,
        "vector_collection": "buffett_kb_wtsht_qwen3_embedding_8b",
        "providers": [
            {
                "id": provider_id,
                "name": "WTSHT",
                "provider": "openai_compatible",
                "base_url": "https://openapi.wtsht.cn/v1",
                "api_key": "",
                "models": [
                    {
                        "id": "DeepSeek-V4-Flash-YR",
                        "capability": "generation",
                        "enabled": True,
                    },
                    {
                        "id": "Qwen3-Embedding-8B",
                        "capability": "embedding",
                        "enabled": True,
                        "dimension": None,
                    },
                    {
                        "id": "Qwen3-Reranker-0.6B",
                        "capability": "reranker",
                        "enabled": True,
                    },
                    {
                        "id": "Qwen3.8-27b",
                        "capability": "generation",
                        "enabled": True,
                    },
                ],
            }
        ],
        "routes": {
            **{task: generation for task in GENERATION_TASKS},
            "embedding": _profile_id(provider_id, "Qwen3-Embedding-8B"),
            "reranker": _profile_id(provider_id, "Qwen3-Reranker-0.6B"),
        },
    }


def settings_exist() -> bool:
    return SETTINGS_PATH.exists()


def load_saved_settings() -> dict[str, Any] | None:
    """Load private settings, including secrets, or return None before first save."""
    with _LOCK:
        if not SETTINGS_PATH.exists():
            return None
        try:
            value = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"模型配置文件无法读取: {exc}") from exc
        return validate_settings(value)


def load_effective_settings() -> dict[str, Any]:
    return load_saved_settings() or default_settings()


def public_settings(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    value = deepcopy(settings or load_effective_settings())
    for provider in value.get("providers", []):
        key = str(provider.pop("api_key", "") or "")
        provider["has_api_key"] = bool(key)
    value["saved"] = settings_exist()
    return value


def _slug(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return clean or "provider"


def validate_settings(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("模型配置必须是 JSON 对象。")
    raw_providers = raw.get("providers")
    if not isinstance(raw_providers, list) or not raw_providers:
        raise ValueError("至少需要一个模型供应商。")

    providers: list[dict[str, Any]] = []
    known_profiles: dict[str, str] = {}
    provider_ids: set[str] = set()
    for index, item in enumerate(raw_providers):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index + 1} 个供应商格式无效。")
        name = str(item.get("name") or f"Provider {index + 1}").strip()
        provider_id = _slug(str(item.get("id") or name))
        if provider_id in provider_ids:
            raise ValueError(f"供应商 ID 重复: {provider_id}")
        provider_ids.add(provider_id)
        provider_type = str(item.get("provider") or "openai_compatible").strip().lower()
        if provider_type not in PROVIDER_TYPES:
            raise ValueError(f"不支持的供应商类型: {provider_type}")
        base_url = str(item.get("base_url") or "").strip().rstrip("/")
        if provider_type != "anthropic" or base_url:
            parsed = urlparse(base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"供应商 {name} 的 API 地址无效。")

        raw_models = item.get("models")
        if not isinstance(raw_models, list) or not raw_models:
            raise ValueError(f"供应商 {name} 至少需要一个模型。")
        models: list[dict[str, Any]] = []
        model_ids: set[str] = set()
        for raw_model in raw_models:
            if not isinstance(raw_model, dict):
                raise ValueError(f"供应商 {name} 包含无效模型。")
            model_id = str(raw_model.get("id") or "").strip()
            capability = str(raw_model.get("capability") or "generation").strip().lower()
            if not model_id:
                raise ValueError(f"供应商 {name} 包含空模型名称。")
            if model_id in model_ids:
                raise ValueError(f"供应商 {name} 的模型名称重复: {model_id}")
            if capability not in CAPABILITIES:
                raise ValueError(f"模型 {model_id} 的能力类型无效。")
            model_ids.add(model_id)
            model = {
                "id": model_id,
                "capability": capability,
                "enabled": bool(raw_model.get("enabled", True)),
            }
            dimension = raw_model.get("dimension")
            if dimension not in (None, ""):
                try:
                    dimension = int(dimension)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"模型 {model_id} 的向量维度必须是整数。") from exc
                if dimension <= 0:
                    raise ValueError(f"模型 {model_id} 的向量维度必须大于 0。")
                model["dimension"] = dimension
            elif capability == "embedding":
                model["dimension"] = None
            models.append(model)
            if model["enabled"]:
                known_profiles[_profile_id(provider_id, model_id)] = capability

        providers.append(
            {
                "id": provider_id,
                "name": name,
                "provider": provider_type,
                "base_url": base_url,
                "api_key": str(item.get("api_key") or "").strip(),
                "models": models,
            }
        )

    routes: dict[str, str] = {}
    raw_routes = raw.get("routes") or {}
    if not isinstance(raw_routes, dict):
        raise ValueError("模型路由格式无效。")
    for route_name in (*GENERATION_TASKS, "embedding", "reranker"):
        profile = str(raw_routes.get(route_name) or "").strip()
        if not profile:
            continue
        capability = known_profiles.get(profile)
        expected = "generation" if route_name in GENERATION_TASKS else route_name
        if capability is None:
            raise ValueError(f"路由 {route_name} 指向不存在或未启用的模型。")
        if capability != expected:
            raise ValueError(f"路由 {route_name} 不能使用 {capability} 模型。")
        routes[route_name] = profile

    for task in GENERATION_TASKS:
        if task not in routes:
            raise ValueError(f"生成任务 {task} 尚未选择模型。")
    if "embedding" not in routes:
        raise ValueError("尚未选择向量模型。")

    vector_collection = str(raw.get("vector_collection") or "buffett_kb").strip()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{1,61}[a-zA-Z0-9]", vector_collection):
        raise ValueError("向量集合名需为 3-63 位字母、数字、点、下划线或短横线。")

    return {
        "version": 1,
        "vector_collection": vector_collection,
        "providers": providers,
        "routes": routes,
    }


def save_settings(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and atomically save settings, preserving omitted/blank keys."""
    with _LOCK:
        existing = load_saved_settings()
        existing_keys = {
            provider["id"]: provider.get("api_key", "")
            for provider in (existing or {}).get("providers", [])
        }
        prepared = deepcopy(raw)
        for provider in prepared.get("providers", []):
            provider_id = _slug(str(provider.get("id") or provider.get("name") or "provider"))
            if provider.get("clear_api_key"):
                provider["api_key"] = ""
            elif not str(provider.get("api_key") or "").strip():
                provider["api_key"] = existing_keys.get(provider_id, "")
            provider.pop("has_api_key", None)
            provider.pop("clear_api_key", None)

        value = validate_settings(prepared)
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = SETTINGS_PATH.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(SETTINGS_PATH)
        return value


def find_profile(settings: dict[str, Any], profile_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    for provider in settings.get("providers", []):
        for model in provider.get("models", []):
            if _profile_id(provider["id"], model["id"]) == profile_id:
                return provider, model
    raise ValueError(f"找不到模型配置: {profile_id}")
