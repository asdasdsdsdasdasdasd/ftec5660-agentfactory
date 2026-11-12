#!/usr/bin/env python3
"""Run AgentFactory Batch 1 (15 questions) one task at a time.

Each question is a separate process so a crash/timeout does not kill the batch.
Token counts come from trajectory.json written by run.py.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_questions(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def summarize_workspace(ws_root, index):
    if not os.path.isdir(ws_root):
        return None
    # run.py writes workspace/<timestamp>/q<index>/
    matches = []
    for ts in sorted(os.listdir(ws_root)):
        qdir = os.path.join(ws_root, ts, f"q{index}")
        traj = os.path.join(qdir, "trajectory.json")
        if os.path.isfile(traj):
            matches.append((os.path.getmtime(traj), qdir, traj))
    if not matches:
        return None
    _, qdir, traj = max(matches)
    with open(traj, "r", encoding="utf-8") as f:
        data = json.load(f)
    usage = data.get("usage") or {}
    meta = usage.get("meta") or {}
    return {
        "workspace": qdir,
        "final_answer": (data.get("final_answer") or "")[:500],
        "total_iterations": data.get("total_iterations"),
        "meta_completion_tokens": meta.get("completion_tokens", 0),
        "meta_prompt_tokens": meta.get("prompt_tokens", 0),
        "meta_calls": meta.get("calls", 0),
        "subagent_completion_tokens": (usage.get("subagent") or {}).get("completion_tokens", 0),
        "usage": usage,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question-file", default="data/questions/questions_round1.jsonl")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None, help="exclusive index")
    parser.add_argument("--skip", type=int, action="append", default=[], help="0-based index to skip (repeatable)")
    parser.add_argument("--tag", default="batch1", help="output dir suffix")
    parser.add_argument("--timeout", type=int, default=3000, help="seconds per question")
    parser.add_argument("--no-save", action="store_true", default=False, help="Pass --no-save to run.py")
    parser.add_argument("--subagent-url", default=None, help="Override SUBAGENT_URL")
    parser.add_argument("--subagent-key", default=None, help="Override SUBAGENT_API_KEY")
    parser.add_argument("--subagent-model", default=None, help="Override SUBAGENT_MODEL")
    args = parser.parse_args()

    qpath = args.question_file
    if not os.path.isabs(qpath):
        qpath = os.path.join(SCRIPT_DIR, qpath)
    questions = load_questions(qpath)
    end = args.end if args.end is not None else len(questions)

    out_dir = os.path.join(
        SCRIPT_DIR,
        "evaluations",
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + args.tag,
    )
    os.makedirs(out_dir, exist_ok=True)
    summary_path = os.path.join(out_dir, "summary.json")
    rows = []
    if os.path.isfile(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            rows = json.load(f).get("tasks", [])

    skip = set(args.skip or [])
    print(f"[eval] output dir: {out_dir}")
    print(f"[eval] questions {args.start}..{end-1} of {len(questions)} skip={sorted(skip)}")

    for i in range(args.start, end):
        if i in skip:
            print(f"[eval] skip q{i}: excluded")
            rows = [r for r in rows if r.get("index") != i] + [{
                "index": i,
                "question": questions[i]["question"],
                "status": "skipped",
            }]
            rows.sort(key=lambda r: r["index"])
            continue  # summary is rewritten after each executed task
        already = next((r for r in rows if r.get("index") == i and r.get("status") == "ok"), None)
        if already:
            print(f"[eval] skip q{i}: already ok")
            continue

        log_path = os.path.join(out_dir, f"q{i:02d}.log")
        print(f"[eval] start q{i}: {questions[i]['question'][:80]}...")
        t0 = time.time()
        returncode = None
        timed_out = False
        child_env = os.environ.copy()
        if args.subagent_url is not None:
            child_env["SUBAGENT_URL"] = args.subagent_url
        if args.subagent_key is not None:
            child_env["SUBAGENT_API_KEY"] = args.subagent_key
        if args.subagent_model is not None:
            child_env["SUBAGENT_MODEL"] = args.subagent_model
        cmd = [sys.executable, "run.py", "--question-file", qpath, "--index", str(i)]
        if args.no_save:
            cmd.append("--no-save")
        with open(log_path, "w", encoding="utf-8") as log:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=SCRIPT_DIR,
                    env=child_env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=args.timeout,
                )
                returncode = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                log.write("\n[eval] TIMEOUT\n")
        elapsed = round(time.time() - t0, 1)
        if timed_out:
            status = "timeout"
        else:
            status = "ok" if returncode == 0 else f"exit_{returncode}"
        info = summarize_workspace(os.path.join(SCRIPT_DIR, "workspace"), i) or {}
        row = {
            "index": i,
            "question": questions[i]["question"],
            "status": status,
            "elapsed_sec": elapsed,
            "log": log_path,
            **info,
        }
        rows = [r for r in rows if r.get("index") != i] + [row]
        rows.sort(key=lambda r: r["index"])
        meta_tokens = [
            r.get("meta_completion_tokens")
            for r in rows
            if r.get("status") == "ok" and r.get("meta_completion_tokens")
        ]
        report = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "question_file": qpath,
            "tag": args.tag,
            "skip": sorted(skip),
            "n_ok": sum(1 for r in rows if r.get("status") == "ok"),
            "n_skipped": sum(1 for r in rows if r.get("status") == "skipped"),
            "n_total": len(questions),
            "avg_meta_completion_tokens": (sum(meta_tokens) / len(meta_tokens)) if meta_tokens else None,
            "paper_table1_agentfactory_batch1": {"opus_4.6": 4324, "sonnet_4.6": 9199},
            "paper_table1_agentfactory_batch2": {"opus_4.6": 2971, "sonnet_4.6": 3862},
            "tasks": rows,
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(
            f"[eval] done q{i} status={status} elapsed={elapsed}s "
            f"meta_tokens={row.get('meta_completion_tokens')} "
            f"avg={report['avg_meta_completion_tokens']}"
        )

    print(f"[eval] summary: {summary_path}")


if __name__ == "__main__":
    main()
