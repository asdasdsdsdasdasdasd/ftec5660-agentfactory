"""
Meta-Agent: An agent that creates, runs, and optimizes question-specific subagents.
Now with Skills support - all actions are unified as skills.
"""

import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load .env configuration
load_dotenv()

# Set runtime environment variables for meta agent
os.environ["LLM_ROLE"] = "meta"
os.environ["LLM_URL"] = os.getenv("META_AGENT_URL", "")
os.environ["LLM_API_KEY"] = os.getenv("META_AGENT_API_KEY", "")
os.environ["LLM_MODEL"] = os.getenv("META_AGENT_MODEL", "")
os.environ["LLM_PROTOCOL"] = os.getenv("META_AGENT_PROTOCOL", "OPENAI_STYLE")

# Get absolute paths based on script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

from llm import reset_usage, snapshot_usage
from meta_agent import MetaAgent


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Meta-Agent for solving questions")
    parser.add_argument("--question-file", default="data/questions/questions_round1.jsonl", help="Path to question file")
    parser.add_argument("--index", type=int, default=None, help="0-based question index to run")
    parser.add_argument("--limit", type=int, default=None, help="Max number of questions to run")
    parser.add_argument("--no-save", action="store_true", default=False,
                        help="Do not save subagent on finish")
    parser.add_argument("--human-confirm", action="store_true", default=False,
                        help="Require human confirmation after each LLM response")

    args = parser.parse_args()

    question_path = args.question_file
    if not os.path.isabs(question_path):
        question_path = os.path.join(SCRIPT_DIR, question_path)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(question_path, "r", encoding="utf-8") as f:
        lines = [ln for ln in f if ln.strip()]

    start = args.index or 0
    end = len(lines) if args.limit is None else min(len(lines), start + args.limit)
    if args.index is not None and args.limit is None:
        end = min(len(lines), start + 1)

    for i in range(start, end):
        data = json.loads(lines[i].strip())
        question = data["question"]
        correct_answer = data.get("answer", None)

        print("=" * 80)
        print(f"QUESTION [{i}]:")
        print(question)
        print("=" * 80)

        reset_usage()
        agent = MetaAgent(
            verbose=True,
            save_on_finish=not args.no_save,
            human_confirm=args.human_confirm
        )

        restart = True
        while restart:
            result = agent.run(question, timestamp, i, correct_answer)
            if result.get("final_answer") == "[Restarted by user]":
                agent = MetaAgent(
                    verbose=True,
                    save_on_finish=not args.no_save,
                    human_confirm=args.human_confirm
                )
                continue
            restart = False

        if result.get("final_answer") == "[Skipped by user]":
            continue

        result["usage"] = snapshot_usage()
        traj_file = os.path.join(agent.current_workspace, "trajectory.json")
        if os.path.exists(traj_file):
            with open(traj_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            saved["usage"] = result["usage"]
            with open(traj_file, "w", encoding="utf-8") as f:
                json.dump(saved, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 80)
        print("FINAL RESULT")
        print("=" * 80)
        print(f"Answer: {result['final_answer']}")
        print(f"Total iterations: {result['total_iterations']}")
        print(f"Usage: {json.dumps(result['usage'])}")


if __name__ == "__main__":
    main()
