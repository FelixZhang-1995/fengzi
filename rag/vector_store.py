"""A lightweight in-memory vector store using term-frequency scoring.

The goal is to stay dependency-light while still illustrating how retrieval
works end-to-end. In production you can swap this with Milvus/PGVector.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List
import json
import math
import re


TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fa5]+", re.UNICODE)


@dataclass
class Document:
    id: str
    title: str
    content: str
    namespace: str
    persona: str
    audience: str
    source: str
    tags: List[str]
    kind: str  # faq | script | news


class InMemoryVectorStore:
    def __init__(self, docs: Iterable[Document]):
        self.docs: List[Document] = list(docs)
        self.index = []
        self.df: Counter = Counter()
        for doc in self.docs:
            token_counts = Counter(tokenize(doc.content + " " + doc.title))
            self.index.append(token_counts)
            for token in token_counts:
                self.df[token] += 1
        self.total_docs = len(self.docs)

    def _tfidf(self, token_counts: Counter) -> Dict[str, float]:
        vec = {}
        for token, tf in token_counts.items():
            idf = math.log((1 + self.total_docs) / (1 + self.df[token])) + 1
            vec[token] = tf * idf
        return vec

    def _cosine(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in set(a) | set(b))
        na = math.sqrt(sum(v * v for v in a.values()))
        nb = math.sqrt(sum(v * v for v in b.values()))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def search(self, query: str, topk: int = 6, namespace: str | None = None, kinds: Iterable[str] | None = None) -> List[Dict]:
        q_tokens = Counter(tokenize(query))
        q_vec = self._tfidf(q_tokens)
        results = []
        for doc, token_counts in zip(self.docs, self.index):
            if namespace and doc.namespace != namespace:
                continue
            if kinds and doc.kind not in kinds:
                continue
            score = self._cosine(q_vec, self._tfidf(token_counts))
            if score == 0:
                continue
            results.append({
                "doc": doc,
                "score": score,
            })
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:topk]


def tokenize(text: str) -> List[str]:
    return TOKEN_PATTERN.findall(text.lower())


def load_jsonl(path: Path) -> List[Dict]:
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        items.append(json.loads(line))
    return items


def build_store(data_root: Path) -> InMemoryVectorStore:
    docs: List[Document] = []
    for kind, relpath in [
        ("faq", "data/curated/faq/faq.jsonl"),
        ("script", "data/curated/scripts/scripts.jsonl"),
        ("news", "data/curated/news/news.jsonl"),
    ]:
        path = data_root / relpath
        if not path.exists():
            continue
        for item in load_jsonl(path):
            docs.append(
                Document(
                    id=item["id"],
                    title=item["title"],
                    content=item["content"],
                    namespace=item.get("namespace", "solar"),
                    persona=item.get("persona", "solar_guide"),
                    audience=item.get("audience", "all"),
                    source=item.get("source", "未知来源"),
                    tags=item.get("tags", []),
                    kind=kind,
                )
            )
    return InMemoryVectorStore(docs)
