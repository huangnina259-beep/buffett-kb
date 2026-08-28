"""Provider-neutral generation gateway.

Business modules address a task (for example ``knowledge_answer``) instead of
instantiating a vendor SDK. Profiles and task routing can be supplied through
environment variables or JSON configuration.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Any, Callable, Iterator, Protocol


class GatewayError(RuntimeError):
    """Base error returned by the generation gateway."""


class GatewayConfigError(GatewayError):
    """The selected model profile is incomplete or unsupported."""


@dataclass(frozen=True)
class ModelProfile:
    name: str
    provider: str
    model: str
    api_key_env: str = ""
    api_key_value: str = ""
    base_url: str | None = None
    timeout: float = 60.0
    max_retries: int = 2
    supports_json_mode: bool = False
    extra_headers: dict[str, str] = field(default_factory=dict)

    @property
    def api_key(self) -> str:
        if self.api_key_value:
            return self.api_key_value
        return os.environ.get(self.api_key_env, "") if self.api_key_env else ""


@dataclass(frozen=True)
class TaskRoute:
    primary: str
    fallbacks: tuple[str, ...] = ()
    max_tokens: int | None = None
    temperature: float | None = None


@dataclass(frozen=True)
class GenerationResult:
    text: str
    provider: str
    model: str
    fallback_used: bool = False
    usage: dict[str, int] = field(default_factory=dict)


class GenerationAdapter(Protocol):
    def complete(
        self,
        profile: ModelProfile,
        *,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float | None,
        json_mode: bool,
    ) -> GenerationResult: ...

    def stream(
        self,
        profile: ModelProfile,
        *,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float | None,
    ) -> Iterator[str]: ...


def _require_key(profile: ModelProfile) -> str:
    key = profile.api_key
    if not key:
        env_name = profile.api_key_env or "the configured API key variable"
        raise GatewayConfigError(
            f"Model profile '{profile.name}' requires {env_name}."
        )
    return key


def _normalise_messages(system: str, messages: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    if system:
        result.append({"role": "system", "content": system})
    for message in messages:
        role = message.get("role", "user")
        if role not in {"system", "user", "assistant"}:
            role = "user"
        result.append({"role": role, "content": str(message.get("content", ""))})
    return result


def _can_fallback(exc: Exception) -> bool:
    """Only transient failures may cross provider boundaries automatically."""
    status = getattr(exc, "status_code", None)
    if status in {400, 401, 403, 404, 413, 422}:
        return False
    if status in {408, 409, 429} or (isinstance(status, int) and status >= 500):
        return True
    return isinstance(exc, (TimeoutError, ConnectionError)) or status is None


class AnthropicAdapter:
    def _client(self, profile: ModelProfile):
        from anthropic import Anthropic

        kwargs: dict[str, Any] = {
            "api_key": _require_key(profile),
            "timeout": profile.timeout,
            "max_retries": profile.max_retries,
        }
        if profile.base_url:
            kwargs["base_url"] = profile.base_url
        if profile.extra_headers:
            kwargs["default_headers"] = profile.extra_headers
        return Anthropic(**kwargs)

    def complete(
        self,
        profile: ModelProfile,
        *,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float | None,
        json_mode: bool,
    ) -> GenerationResult:
        kwargs: dict[str, Any] = {
            "model": profile.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        response = self._client(profile).messages.create(**kwargs)
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        usage = {
            "input_tokens": int(getattr(response.usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(response.usage, "output_tokens", 0) or 0),
        }
        return GenerationResult(text=text, provider=profile.provider, model=profile.model, usage=usage)

    def stream(
        self,
        profile: ModelProfile,
        *,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float | None,
    ) -> Iterator[str]:
        kwargs: dict[str, Any] = {
            "model": profile.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        with self._client(profile).messages.stream(**kwargs) as stream:
            yield from stream.text_stream


class OpenAICompatibleAdapter:
    """OpenAI and any service implementing the Chat Completions contract."""

    def _client(self, profile: ModelProfile):
        from openai import OpenAI

        kwargs: dict[str, Any] = {
            "api_key": _require_key(profile),
            "timeout": profile.timeout,
            "max_retries": profile.max_retries,
        }
        if profile.base_url:
            kwargs["base_url"] = profile.base_url
        if profile.extra_headers:
            kwargs["default_headers"] = profile.extra_headers
        return OpenAI(**kwargs)

    def complete(
        self,
        profile: ModelProfile,
        *,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float | None,
        json_mode: bool,
    ) -> GenerationResult:
        kwargs: dict[str, Any] = {
            "model": profile.model,
            "max_tokens": max_tokens,
            "messages": _normalise_messages(system, messages),
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if json_mode and profile.supports_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self._client(profile).chat.completions.create(**kwargs)
        text = response.choices[0].message.content or ""
        raw_usage = getattr(response, "usage", None)
        usage = {
            "input_tokens": int(getattr(raw_usage, "prompt_tokens", 0) or 0),
            "output_tokens": int(getattr(raw_usage, "completion_tokens", 0) or 0),
        }
        return GenerationResult(text=text, provider=profile.provider, model=profile.model, usage=usage)

    def stream(
        self,
        profile: ModelProfile,
        *,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float | None,
    ) -> Iterator[str]:
        kwargs: dict[str, Any] = {
            "model": profile.model,
            "max_tokens": max_tokens,
            "messages": _normalise_messages(system, messages),
            "stream": True,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        for chunk in self._client(profile).chat.completions.create(**kwargs):
            text = chunk.choices[0].delta.content if chunk.choices else None
            if text:
                yield text


AdapterFactory = Callable[[], GenerationAdapter]


DEFAULT_TASKS = (
    "knowledge_answer",
    "tutor_dialogue",
    "coach_dialogue",
    "structured_feedback",
    "long_synthesis",
    "daily_digest",
)


def _json_env(name: str) -> dict[str, Any]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GatewayConfigError(f"{name} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise GatewayConfigError(f"{name} must contain a JSON object.")
    return value


def _provider_key_env(provider: str) -> str:
    return {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "minimax": "MINIMAX_API_KEY",
    }.get(provider, "AI_API_KEY")


def _provider_base_url(provider: str) -> str | None:
    if provider == "gemini":
        return "https://generativelanguage.googleapis.com/v1beta/openai/"
    return None


def _default_profiles() -> dict[str, ModelProfile]:
    provider = os.environ.get("AI_PROVIDER", "anthropic").strip().lower()
    model = os.environ.get("AI_MODEL")
    legacy_model = os.environ.get("LLM_MODEL", "")
    if not model and (provider != "anthropic" or legacy_model.lower().startswith("claude")):
        model = legacy_model
    if not model:
        model = "claude-sonnet-4-6" if provider == "anthropic" else ""
    base_url = os.environ.get("AI_BASE_URL") or _provider_base_url(provider)
    key_env = os.environ.get("AI_API_KEY_ENV") or _provider_key_env(provider)

    profiles = {
        "default": ModelProfile(
            name="default",
            provider=provider,
            model=model,
            api_key_env=key_env,
            base_url=base_url,
            supports_json_mode=provider == "openai",
        )
    }
    if os.environ.get("MINIMAX_API_KEY"):
        profiles["minimax_legacy"] = ModelProfile(
            name="minimax_legacy",
            provider="openai_compatible",
            model=os.environ.get("DIGEST_MODEL")
            or os.environ.get("LLM_MODEL")
            or "MiniMax-Text-01",
            api_key_env="MINIMAX_API_KEY",
            base_url=os.environ.get("MINIMAX_BASE_URL")
            or os.environ.get("LLM_BASE_URL", "https://api.minimax.io/v1"),
        )
    return profiles


def load_profiles() -> dict[str, ModelProfile]:
    from ai_settings import find_profile, load_saved_settings

    saved = load_saved_settings()
    if saved:
        profiles: dict[str, ModelProfile] = {}
        generation_ids = {
            profile_id
            for task, profile_id in saved["routes"].items()
            if task in DEFAULT_TASKS
        }
        for profile_id in generation_ids:
            provider, model = find_profile(saved, profile_id)
            provider_type = provider["provider"]
            profiles[profile_id] = ModelProfile(
                name=profile_id,
                provider=provider_type,
                model=model["id"],
                api_key_value=provider.get("api_key", ""),
                base_url=provider.get("base_url") or _provider_base_url(provider_type),
                supports_json_mode=provider_type in {"openai", "openai_compatible", "gemini"},
            )
        return profiles

    profiles = _default_profiles()
    for name, raw in _json_env("AI_PROFILES_JSON").items():
        if not isinstance(raw, dict):
            raise GatewayConfigError(f"Profile '{name}' must be an object.")
        provider = str(raw.get("provider", "openai_compatible")).lower()
        headers = raw.get("extra_headers") or {}
        profiles[name] = ModelProfile(
            name=name,
            provider=provider,
            model=str(raw.get("model", "")),
            api_key_env=str(raw.get("api_key_env") or _provider_key_env(provider)),
            base_url=raw.get("base_url") or _provider_base_url(provider),
            timeout=float(raw.get("timeout", 60)),
            max_retries=int(raw.get("max_retries", 2)),
            supports_json_mode=bool(raw.get("supports_json_mode", provider == "openai")),
            extra_headers={str(k): str(v) for k, v in headers.items()},
        )
    return profiles


def load_task_routes(profiles: dict[str, ModelProfile]) -> dict[str, TaskRoute]:
    from ai_settings import load_saved_settings

    saved = load_saved_settings()
    if saved:
        return {
            task: TaskRoute(primary=saved["routes"][task])
            for task in DEFAULT_TASKS
        }

    default_profile = "default"
    routes = {task: TaskRoute(primary=default_profile) for task in DEFAULT_TASKS}
    if "minimax_legacy" in profiles:
        routes["daily_digest"] = TaskRoute(primary="minimax_legacy")

    for task, raw in _json_env("AI_TASKS_JSON").items():
        if isinstance(raw, str):
            routes[task] = TaskRoute(primary=raw)
        elif isinstance(raw, dict):
            routes[task] = TaskRoute(
                primary=str(raw.get("primary", default_profile)),
                fallbacks=tuple(str(x) for x in raw.get("fallbacks", [])),
                max_tokens=int(raw["max_tokens"]) if raw.get("max_tokens") is not None else None,
                temperature=float(raw["temperature"])
                if raw.get("temperature") is not None
                else None,
            )
        else:
            raise GatewayConfigError(f"Task route '{task}' must be a string or object.")

    for task in set(DEFAULT_TASKS) | set(routes):
        env_prefix = f"AI_TASK_{task.upper()}"
        primary = os.environ.get(f"{env_prefix}_PROFILE")
        if primary:
            current = routes.get(task, TaskRoute(primary=default_profile))
            fallbacks = tuple(
                x.strip()
                for x in os.environ.get(f"{env_prefix}_FALLBACKS", "").split(",")
                if x.strip()
            )
            routes[task] = TaskRoute(
                primary=primary,
                fallbacks=fallbacks,
                max_tokens=current.max_tokens,
                temperature=current.temperature,
            )
    return routes


class GenerationGateway:
    def __init__(
        self,
        profiles: dict[str, ModelProfile] | None = None,
        routes: dict[str, TaskRoute] | None = None,
        adapters: dict[str, AdapterFactory] | None = None,
    ) -> None:
        self.profiles = profiles or load_profiles()
        self.routes = routes or load_task_routes(self.profiles)
        self.adapters: dict[str, AdapterFactory] = adapters or {
            "anthropic": AnthropicAdapter,
            "openai": OpenAICompatibleAdapter,
            "openai_compatible": OpenAICompatibleAdapter,
            "gemini": OpenAICompatibleAdapter,
            "minimax": OpenAICompatibleAdapter,
        }

    def _route(self, task: str) -> TaskRoute:
        route = self.routes.get(task) or self.routes.get("knowledge_answer")
        if not route:
            raise GatewayConfigError(f"No model route configured for task '{task}'.")
        return route

    def _route_profiles(self, task: str) -> list[ModelProfile]:
        route = self._route(task)
        result = []
        for name in (route.primary, *route.fallbacks):
            profile = self.profiles.get(name)
            if not profile:
                raise GatewayConfigError(f"Task '{task}' references unknown profile '{name}'.")
            env_model = os.environ.get(f"AI_TASK_{task.upper()}_MODEL")
            if not env_model and task == "tutor_dialogue":
                env_model = os.environ.get("TUTOR_MODEL")
            if env_model and name == route.primary:
                profile = replace(profile, model=env_model)
            if not profile.model:
                raise GatewayConfigError(f"Model profile '{profile.name}' has no model ID.")
            result.append(profile)
        return result

    def _adapter(self, profile: ModelProfile) -> GenerationAdapter:
        factory = self.adapters.get(profile.provider)
        if not factory:
            raise GatewayConfigError(
                f"Unsupported generation provider '{profile.provider}' in profile '{profile.name}'."
            )
        return factory()

    def complete(
        self,
        task: str,
        *,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> GenerationResult:
        route = self._route(task)
        max_tokens = route.max_tokens or max_tokens
        if route.temperature is not None:
            temperature = route.temperature
        failures: list[str] = []
        for index, profile in enumerate(self._route_profiles(task)):
            try:
                result = self._adapter(profile).complete(
                    profile,
                    system=system,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_mode=json_mode,
                )
                return replace(result, fallback_used=index > 0)
            except GatewayConfigError:
                raise
            except Exception as exc:
                logging.warning(
                    "[AI] task=%s profile=%s failed: %s", task, profile.name, exc
                )
                if not _can_fallback(exc):
                    raise GatewayError(
                        "The configured model rejected the request. Check server logs for details."
                    ) from exc
                failures.append(f"{profile.name}: {exc}")
        raise GatewayError("All configured models failed. Check server logs for details.")

    def stream(
        self,
        task: str,
        *,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float | None = None,
    ) -> Iterator[str]:
        route = self._route(task)
        max_tokens = route.max_tokens or max_tokens
        if route.temperature is not None:
            temperature = route.temperature
        failures: list[str] = []
        for profile in self._route_profiles(task):
            emitted = False
            try:
                for text in self._adapter(profile).stream(
                    profile,
                    system=system,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                ):
                    emitted = True
                    yield text
                return
            except GatewayConfigError:
                raise
            except Exception as exc:
                if emitted:
                    raise GatewayError(
                        "The streaming model failed after output began. Check server logs for details."
                    ) from exc
                logging.warning(
                    "[AI] streaming task=%s profile=%s failed before output: %s",
                    task,
                    profile.name,
                    exc,
                )
                if not _can_fallback(exc):
                    raise GatewayError(
                        "The configured streaming model rejected the request. "
                        "Check server logs for details."
                    ) from exc
                failures.append(f"{profile.name}: {exc}")
        raise GatewayError("All configured models failed. Check server logs for details.")

    def status(self) -> dict[str, Any]:
        return {
            "profiles": {
                name: {
                    "provider": profile.provider,
                    "model": profile.model,
                    "configured": bool(profile.model and profile.api_key),
                }
                for name, profile in self.profiles.items()
            },
            "tasks": {
                name: {
                    "primary": route.primary,
                    "fallbacks": list(route.fallbacks),
                    "max_tokens": route.max_tokens,
                    "temperature": route.temperature,
                }
                for name, route in self.routes.items()
            },
        }


@lru_cache(maxsize=1)
def get_generation_gateway() -> GenerationGateway:
    return GenerationGateway()


def reset_generation_gateway() -> None:
    get_generation_gateway.cache_clear()


def parse_json_text(text: str) -> Any:
    """Parse a model JSON response while tolerating a surrounding code fence."""
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("```", 2)[1]
        if clean.lstrip().lower().startswith("json"):
            clean = clean.lstrip()[4:]
    return json.loads(clean.strip())
