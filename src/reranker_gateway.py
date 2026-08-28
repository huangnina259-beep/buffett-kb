"""Optional provider-neutral reranking for retrieved knowledge-base chunks."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence


class RerankerError(RuntimeError):
    pass


@dataclass(frozen=True)
class RerankerProfile:
    name: str
    provider: str
    model: str
    base_url: str
    api_key: str
    timeout: float = 45.0


@dataclass(frozen=True)
class RerankedItem:
    index: int
    score: float


class RerankerGateway:
    def __init__(self, profile: RerankerProfile | None = None) -> None:
        self.profile = profile or load_reranker_profile()

    @property
    def configured(self) -> bool:
        return bool(self.profile and self.profile.model and self.profile.api_key)

    def rerank(self, query: str, documents: Sequence[str], top_n: int) -> list[RerankedItem]:
        if not self.profile or not self.configured:
            return []
        if not documents:
            return []
        if self.profile.provider == "anthropic":
            raise RerankerError("Anthropic 供应商不支持通用 rerank 接口。")

        import httpx

        endpoint = f"{self.profile.base_url.rstrip('/')}/rerank"
        payload = {
            "model": self.profile.model,
            "query": query,
            "documents": list(documents),
            "top_n": min(max(1, top_n), len(documents)),
            "return_documents": False,
        }
        try:
            response = httpx.post(
                endpoint,
                headers={"Authorization": f"Bearer {self.profile.api_key}"},
                json=payload,
                timeout=self.profile.timeout,
            )
            response.raise_for_status()
            data = response.json()
            raw_results = data.get("results") or data.get("data") or []
            results = []
            for item in raw_results:
                index = item.get("index")
                score = item.get("relevance_score", item.get("score"))
                if index is None or score is None:
                    continue
                index = int(index)
                if 0 <= index < len(documents):
                    results.append(RerankedItem(index=index, score=float(score)))
            if not results:
                raise RerankerError("重排接口未返回可识别的 results/index/score 数据。")
            return results
        except RerankerError:
            raise
        except Exception as exc:
            logging.warning("[Reranker] profile=%s failed: %s", self.profile.name, exc)
            status = getattr(getattr(exc, "response", None), "status_code", None)
            message = f"重排请求失败{f'（HTTP {status}）' if status else ''}。"
            raise RerankerError(message) from exc

    def status(self) -> dict:
        if not self.profile:
            return {"enabled": False, "configured": False}
        return {
            "enabled": True,
            "configured": self.configured,
            "provider": self.profile.provider,
            "model": self.profile.model,
        }


def load_reranker_profile() -> RerankerProfile | None:
    from ai_settings import find_profile, load_saved_settings

    saved = load_saved_settings()
    if not saved:
        return None
    active = saved["routes"].get("reranker")
    if not active:
        return None
    provider, model = find_profile(saved, active)
    return RerankerProfile(
        name=active,
        provider=provider["provider"],
        model=model["id"],
        base_url=provider.get("base_url", ""),
        api_key=provider.get("api_key", ""),
    )


@lru_cache(maxsize=1)
def get_reranker_gateway() -> RerankerGateway:
    return RerankerGateway()


def reset_reranker_gateway() -> None:
    get_reranker_gateway.cache_clear()
