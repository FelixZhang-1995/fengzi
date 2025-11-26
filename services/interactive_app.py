"""Interactive CLI simulating a visitor talking to the exhibition screen."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from services.orchestrator import Orchestrator


WELCOME = (
    "您好，欢迎来到北京天文馆！我可以为您讲解展品、解答问题，" "输入问题后按回车即可，输入 `exit` 退出。"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the interactive Q&A demo.")
    parser.add_argument("--persona", default="solar_guide", help="Persona id: solar_guide|deep_space_guide|kids_guide")
    args = parser.parse_args()

    orchestrator = Orchestrator(BASE_DIR)

    print(WELCOME)
    while True:
        try:
            query = input("游客：").strip()
        except EOFError:
            break
        if not query:
            continue
        if query.lower() in {"exit", "quit", "q"}:
            print("讲解员：感谢参观，期待下次见面！")
            break
        answer = orchestrator.handle_query(query, {"persona": args.persona})
        print("讲解员：")
        print(answer.message)
        if answer.citations:
            print(f"参考资料 ID：{', '.join(answer.citations)}")


if __name__ == "__main__":
    main()
