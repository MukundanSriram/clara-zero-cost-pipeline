#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

import urllib.request
import urllib.error


def create_asana_task(account_id: str, memo: Dict[str, Any]) -> Optional[str]:
    access_token = os.environ.get("ASANA_ACCESS_TOKEN")
    project_id = os.environ.get("ASANA_PROJECT_ID")
    if not access_token or not project_id:
        return None

    url = "https://app.asana.com/api/1.0/tasks"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    name = f"Configure Clara agent for account {account_id}"
    notes_lines = [
        f"Account ID: {account_id}",
        f"Company: {memo.get('company_name', '')}",
        "",
        "This task was auto-created by the Clara zero-cost pipeline.",
        "Outputs are stored under outputs/accounts/<account_id>/v1.",
    ]
    data = {
        "data": {
            "name": name,
            "notes": "\n".join(notes_lines),
            "projects": [project_id],
        }
    }
    body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            task_gid = resp_data.get("data", {}).get("gid")
            return task_gid
    except urllib.error.URLError as exc:
        print(f"Asana API error: {exc}")
        return None


def append_local_task_log(account_id: str, memo: Dict[str, Any], outputs_base: str = "outputs") -> None:
    log_dir = os.path.join(outputs_base, "tasks")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "local_tasks.json")

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "account_id": account_id,
        "company_name": memo.get("company_name", ""),
        "memo_path": f"outputs/accounts/{account_id}/v1/memo.json",
        "status": "pending",
    }

    existing = []
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    existing.append(entry)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a task item in Asana (if configured) or local log.")
    parser.add_argument("--account-id", required=True, help="Account ID")
    parser.add_argument("--memo", required=True, help="Path to memo JSON")
    args = parser.parse_args()

    with open(args.memo, "r", encoding="utf-8") as f:
        memo = json.load(f)

    task_gid = create_asana_task(args.account_id, memo)
    if task_gid:
        print(f"Created Asana task for {args.account_id}: {task_gid}")
    else:
        print("Asana not configured or failed; logging task locally instead.")
        append_local_task_log(args.account_id, memo)


if __name__ == "__main__":
    main()

