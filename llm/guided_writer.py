"""Simple deterministic writer to compose answers from retrieved contexts.

This is intentionally dependency-light and transparent so beginners can read the
logic. Replace with an actual LLM call when ready.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict

from rag.vector_store import Document


@dataclass
class Persona:
    name: str
    style: str


@dataclass
class Answer:
    message: str
    citations: List[str]


def load_personas(config: Dict) -> Dict[str, Persona]:
    personas = {}
    for pid, content in config.get("personas", {}).items():
        personas[pid] = Persona(name=content.get("name", pid), style=content.get("style", ""))
    return personas


def render_answer(query: str, persona: Persona, contexts: List[Document]) -> Answer:
    citation_labels = []
    bullet_points = []
    for doc in contexts:
        bullet_points.append(f"- 来源《{doc.title}》：{doc.content}")
        citation_labels.append(doc.id)
    intro = f"{persona.name}：{persona.style.strip()}"
    summary = f"\n\n游客提问：{query}\n" if query else "\n"
    body = "\n".join(bullet_points) if bullet_points else "暂未找到相关资料，但我会继续学习并更新库。"
    message = intro + summary + body
    return Answer(message=message, citations=citation_labels)
