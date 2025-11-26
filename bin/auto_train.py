#!/usr/bin/env python3
"""Auto-generate a minimal training artifact from curated data.

This does NOT fine-tune a real LLM (that would require GPU and time). Instead it
creates a lightweight keyword-to-snippet cache that the demo app can read to
simulate "已经自动训练"，并写出模型元数据，避免用户手填配置。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

BASE = Path(__file__).resolve().parent.parent
CURATED_DIR = BASE / "data/curated"
MODEL_DIR = BASE / "models"


def load_curated() -> List[Dict]:
    chunks: List[Dict] = []
    for path in (CURATED_DIR / "faq").glob("*.jsonl"):
        chunks.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    for path in (CURATED_DIR / "scripts").glob("*.jsonl"):
        chunks.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    for path in (CURATED_DIR / "news").glob("*.jsonl"):
        chunks.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    return chunks


def build_keyword_cache(chunks: List[Dict]) -> Dict[str, List[str]]:
    cache: Dict[str, List[str]] = {}
    for rec in chunks:
        tokens = set(rec.get("title", "").split()) | set(rec.get("tags", []))
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            cache.setdefault(token, []).append(rec.get("content", ""))
    return cache


def write_artifacts(cache: Dict[str, List[str]]) -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    (MODEL_DIR / "trained_stub.json").write_text(
        json.dumps({"keyword_cache": cache}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (MODEL_DIR / "MODEL_CARD.md").write_text(
        (
            "# Auto-trained stub model\n\n"
            "本模型卡仅示意：脚本根据 data/curated 的知识片段自动生成关键字缓存，"
            "在无 GPU 的演示环境下模拟‘已训练’状态。\n"
            "- 本地默认模型: Qwen2-1.5B-Instruct (GGUF 量化占位路径)\n"
            "- 联网默认模型: 通义千问 Qwen-Max API (配置见 configs/models.yaml)\n"
        ),
        encoding="utf-8",
    )


def ensure_placeholder_weight():
    models_cfg = BASE / "configs/models.yaml"
    if not models_cfg.exists():
        return
    cfg_text = models_cfg.read_text(encoding="utf-8")
    for line in cfg_text.splitlines():
        if line.strip().startswith("path:"):
            path = line.split(":", 1)[1].strip()
            weight_path = BASE / path
            weight_path.parent.mkdir(parents=True, exist_ok=True)
            if not weight_path.exists():
                weight_path.write_text(
                    "占位符：请将 Qwen2-1.5B-Instruct GGUF 权重放在此处，或继续使用 demo stub。\n",
                    encoding="utf-8",
                )
            break


def main():
    chunks = load_curated()
    cache = build_keyword_cache(chunks)
    write_artifacts(cache)
    ensure_placeholder_weight()
    print("Auto-train complete: models/trained_stub.json ready; placeholder weight ensured if absent.")


if __name__ == "__main__":
    main()
