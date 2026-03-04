#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
from typing import List


def _infer_account_id(filename: str) -> str:
    basename = os.path.basename(filename)
    return re.split(r"_demo|_onboarding", basename, maxsplit=1)[0]


def list_demo_files(demo_dir: str) -> List[str]:
    files: List[str] = []
    for name in os.listdir(demo_dir):
        if name.lower().endswith(".txt"):
            files.append(os.path.join(demo_dir, name))
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch process demo transcripts into v1 memo + agent spec.")
    parser.add_argument("--demo-dir", required=True, help="Directory containing demo transcripts (.txt)")
    parser.add_argument("--outputs-dir", required=True, help="Base outputs directory (e.g. outputs/accounts)")
    args = parser.parse_args()

    demo_files = list_demo_files(args.demo_dir)
    if not demo_files:
        print(f"No .txt files found in {args.demo_dir}")
        return

    for path in demo_files:
        account_id = _infer_account_id(path)
        account_dir_v1 = os.path.join(args.outputs_dir, account_id, "v1")
        os.makedirs(account_dir_v1, exist_ok=True)

        memo_path = os.path.join(account_dir_v1, "memo.json")
        spec_path = os.path.join(account_dir_v1, "agent_spec.json")

        print(f"Processing demo transcript for account '{account_id}': {path}")

        # 1) Extract memo
        subprocess.run(
            [
                "python3",
                os.path.join("scripts", "extract_account_memo.py"),
                "--input",
                path,
                "--account-id",
                account_id,
                "--output",
                memo_path,
            ],
            check=True,
        )

        # 2) Generate v1 agent spec
        subprocess.run(
            [
                "python3",
                os.path.join("scripts", "generate_agent_spec.py"),
                "--memo",
                memo_path,
                "--version",
                "v1",
                "--output",
                spec_path,
            ],
            check=True,
        )

        # 3) Optionally create a task item (Asana or local log)
        try:
            subprocess.run(
                [
                    "python3",
                    os.path.join("scripts", "create_task_item.py"),
                    "--account-id",
                    account_id,
                    "--memo",
                    memo_path,
                ],
                check=True,
            )
        except FileNotFoundError:
            # If create_task_item.py is missing, skip silently.
            print("create_task_item.py not found; skipping task creation.")
        except subprocess.CalledProcessError as exc:
            print(f"Task creation failed for {account_id}: {exc}")

    # For convenience, write a simple run summary
    summary_path = os.path.join(args.outputs_dir, "demo_run_summary.json")
    summary = {
        "demo_dir": args.demo_dir,
        "accounts_processed": [_infer_account_id(p) for p in demo_files],
    }
    os.makedirs(args.outputs_dir, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()

