#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
from typing import Any, Dict, List, Tuple


def _infer_account_id(filename: str) -> str:
    basename = os.path.basename(filename)
    return re.split(r"_demo|_onboarding", basename, maxsplit=1)[0]


def list_onboarding_files(onboarding_dir: str) -> List[str]:
    files: List[str] = []
    for name in os.listdir(onboarding_dir):
        if name.lower().endswith(".txt"):
            files.append(os.path.join(onboarding_dir, name))
    return sorted(files)


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def apply_memo_patch(v1: Dict[str, Any], patch: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Apply a conservative patch:
    - For each top-level field, if patch[field] is non-empty / non-null, override v1[field].
    - Returns (v2, diff) where diff[field] = {"old": ..., "new": ...} for changed fields.
    """
    v2 = json.loads(json.dumps(v1))  # deep copy
    diff: Dict[str, Any] = {}

    for key, new_value in patch.items():
        old_value = v1.get(key)
        # Skip account_id or core identity unless explicitly changed
        if key == "account_id":
            continue

        # Determine if new_value is "substantial"
        is_substantial = False
        if isinstance(new_value, (list, dict)):
            is_substantial = bool(new_value)
        elif isinstance(new_value, str):
            is_substantial = new_value.strip() != ""
        elif new_value is not None:
            is_substantial = True

        if not is_substantial:
            continue

        if old_value != new_value:
            v2[key] = new_value
            diff[key] = {"old": old_value, "new": new_value}

    return v2, diff


def write_changelog(markdown_path: str, json_path: str, account_id: str, field_diff: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(markdown_path), exist_ok=True)

    # JSON diff
    _save_json(json_path, {"account_id": account_id, "changes": field_diff})

    # Markdown diff
    lines: List[str] = []
    lines.append(f"# Changelog for {account_id}")
    lines.append("")
    if not field_diff:
        lines.append("No changes detected between v1 and v2.")
    else:
        for field, change in field_diff.items():
            lines.append(f"- **{field}**")
            lines.append(f"  - Old: `{json.dumps(change['old'], ensure_ascii=False)}`")
            lines.append(f"  - New: `{json.dumps(change['new'], ensure_ascii=False)}`")
    content = "\n".join(lines) + "\n"

    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch process onboarding transcripts into v2 memo + agent spec + changelog.")
    parser.add_argument("--onboarding-dir", required=True, help="Directory containing onboarding transcripts (.txt)")
    parser.add_argument("--outputs-dir", required=True, help="Base outputs directory (e.g. outputs/accounts)")
    parser.add_argument("--changelog-dir", required=True, help="Directory to write per-account changelog files")
    args = parser.parse_args()

    onboarding_files = list_onboarding_files(args.onboarding_dir)
    if not onboarding_files:
        print(f"No .txt files found in {args.onboarding_dir}")
        return

    for path in onboarding_files:
        account_id = _infer_account_id(path)
        print(f"Processing onboarding transcript for account '{account_id}': {path}")

        account_dir_v1 = os.path.join(args.outputs_dir, account_id, "v1")
        account_dir_v2 = os.path.join(args.outputs_dir, account_id, "v2")

        v1_memo_path = os.path.join(account_dir_v1, "memo.json")
        v1_spec_path = os.path.join(account_dir_v1, "agent_spec.json")
        if not os.path.exists(v1_memo_path):
            print(f"Skipping {account_id}: v1 memo not found at {v1_memo_path}")
            continue
        if not os.path.exists(v1_spec_path):
            print(f"Warning: v1 agent spec not found at {v1_spec_path} (will still generate v2).")

        # 1) Extract memo from onboarding transcript (patch candidate)
        onboarding_memo_path = os.path.join(account_dir_v2, "memo_from_onboarding.json")
        os.makedirs(account_dir_v2, exist_ok=True)
        subprocess.run(
            [
                "python3",
                os.path.join("scripts", "extract_account_memo.py"),
                "--input",
                path,
                "--account-id",
                account_id,
                "--output",
                onboarding_memo_path,
            ],
            check=True,
        )

        v1_memo = _load_json(v1_memo_path)
        onboarding_memo = _load_json(onboarding_memo_path)

        # 2) Apply patch to derive v2 memo
        v2_memo, field_diff = apply_memo_patch(v1_memo, onboarding_memo)
        v2_memo_path = os.path.join(account_dir_v2, "memo.json")
        _save_json(v2_memo_path, v2_memo)

        # 3) Generate v2 agent spec
        v2_spec_path = os.path.join(account_dir_v2, "agent_spec.json")
        subprocess.run(
            [
                "python3",
                os.path.join("scripts", "generate_agent_spec.py"),
                "--memo",
                v2_memo_path,
                "--version",
                "v2",
                "--output",
                v2_spec_path,
            ],
            check=True,
        )

        # 4) Write changelog (markdown + json)
        markdown_path = os.path.join(args.changelog_dir, f"{account_id}.md")
        json_path = os.path.join(args.changelog_dir, f"{account_id}.json")
        write_changelog(markdown_path, json_path, account_id, field_diff)

    print("Onboarding processing complete.")


if __name__ == "__main__":
    main()

