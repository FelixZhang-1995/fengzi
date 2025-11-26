"""Simple orchestrator that combines routing, retrieval, and answer rendering."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Dict

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from llm.guided_writer import Answer, load_personas, render_answer
from rag.router import route
from rag.search import create_search_engine


def parse_personas_config(config_path: Path) -> Dict:
    try:
        import yaml

        return yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception:
        data: Dict[str, Dict[str, str]] = {"personas": {}}
        current = None
        for line in config_path.read_text(encoding="utf-8").splitlines():
            line = line.rstrip()
            if not line or line.strip().startswith("#"):
                continue
            if not line.startswith("  ") and ":" in line:
                continue
            if line.startswith("  ") and not line.startswith("    "):
                current = line.strip().rstrip(":")
                data["personas"][current] = {}
            elif line.startswith("    ") and current:
                key, _, value = line.strip().partition(":")
                data["personas"][current][key.strip()] = value.strip()
        return data


class Orchestrator:
    def __init__(self, base_dir: Path = BASE_DIR):
        self.base_dir = base_dir
        self.personas = self._load_personas()
        self.search_engine = create_search_engine(base_dir)

    def _load_personas(self):
        config_path = self.base_dir / "configs/personas.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Missing personas config at {config_path}")
        config = parse_personas_config(config_path)
        return load_personas(config)

    def handle_query(self, query: str, metadata: Dict) -> Answer:
        plan = route(query, metadata)
        search_results = self.search_engine.search(query, plan)
        docs = [r["doc"] for r in search_results]
        persona = self.personas.get(plan.persona or metadata.get("persona") or "solar_guide")
        return render_answer(query, persona, docs)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run a single-turn query through the orchestrator.")
    parser.add_argument("query", type=str, nargs="?", default="给我介绍一下太阳黑子", help="User question")
    parser.add_argument("--persona", default="solar_guide", help="Persona id from configs/personas.yaml")
    args = parser.parse_args()

    orch = Orchestrator(BASE_DIR)
    answer = orch.handle_query(args.query, {"persona": args.persona})
    print(json.dumps(asdict(answer), ensure_ascii=False, indent=2))
