"""Intent routing for the astronomy RAG pipeline.

This module keeps the logic simple but explicit so newcomers can trace how
queries map to namespaces and retrieval strategies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RoutePlan:
    namespace: str
    topk: int = 6
    rerank: bool = True
    include_news: bool = True
    include_scripts: bool = True
    include_faq: bool = True
    persona: Optional[str] = None
    audience: Optional[str] = None


def detect_intent(query: str) -> str:
    normalized = query.lower()
    if "路线" in query or "怎么走" in query:
        return "navigation"
    if "新闻" in query or "最近" in query:
        return "news"
    if "孩子" in query or "小朋友" in query:
        return "kids"
    if "图片" in query or "照片" in query:
        return "vision"
    return "general"


def route(query: str, metadata: Dict) -> RoutePlan:
    intent = detect_intent(query)
    default_persona = metadata.get("persona") or "solar_guide"
    persona = default_persona
    namespace = metadata.get("namespace") or "solar"
    audience = metadata.get("audience")

    if intent == "kids":
        namespace = "kids"
        persona = "kids_guide"
        audience = audience or "kid"
    elif intent == "news":
        namespace = metadata.get("namespace", "solar")
    elif intent == "vision":
        # Vision path would combine image and text; here we just keep namespace.
        namespace = metadata.get("namespace", "solar")
    elif intent == "navigation":
        namespace = "map"
        return RoutePlan(namespace=namespace, topk=3, rerank=False, include_scripts=True, include_faq=False, include_news=False)

    return RoutePlan(
        namespace=namespace,
        persona=persona,
        audience=audience,
        topk=8 if intent != "kids" else 4,
        rerank=intent != "kids",
        include_news=intent in {"news", "general"},
    )
