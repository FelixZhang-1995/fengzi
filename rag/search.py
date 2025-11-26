"""Search wrapper combining routing plan and vector store."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

from rag.router import RoutePlan
from rag.vector_store import InMemoryVectorStore, build_store


class SearchEngine:
    def __init__(self, data_root: Path):
        self.store = build_store(data_root)

    def search(self, query: str, plan: RoutePlan) -> List[Dict]:
        kinds: List[str] = []
        if plan.include_faq:
            kinds.append("faq")
        if plan.include_scripts:
            kinds.append("script")
        if plan.include_news:
            kinds.append("news")
        return self.store.search(query, topk=plan.topk, namespace=plan.namespace, kinds=kinds)


def create_search_engine(data_root: str | Path) -> SearchEngine:
    return SearchEngine(Path(data_root))
