"""
Remove duplicate tasks and filter out low-quality tasks from Label Studio.

Keeps per duplicate group:
  - labeled tasks (have annotations) first
  - then the task with the most complete code (longest body)

Removes:
  - signature-only code tasks (single-line code)
  - excess duplicates (same query, keep best one)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from label_studio_client import (
    BASE_URL,
    api_headers,
    ensure_project,
    login_session,
    parse_results,
)


def fetch_all_tasks(session, headers, project_id):
    tasks, page = [], 1
    while True:
        url = f"{BASE_URL}/api/tasks/?project={project_id}&page={page}&page_size=100"
        res = session.get(url, headers=headers, timeout=120)
        if res.status_code == 404:
            break
        res.raise_for_status()
        batch = parse_results(res.json())
        if not batch:
            break
        tasks.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return tasks


def is_signature_only(code):
    lines = [l for l in code.strip().splitlines() if l.strip()]
    return len(lines) <= 1


def task_score(task):
    """Higher = better to keep. Labeled tasks always win."""
    annotations = len(task.get("annotations") or [])
    code_len = len(task.get("data", {}).get("code", ""))
    return (annotations * 100_000) + code_len


def delete_task(session, headers, task_id):
    url = f"{BASE_URL}/api/tasks/{task_id}/"
    res = session.delete(url, headers=headers, timeout=60)
    return res.status_code in (200, 204)


def main():
    print(f"Target: {BASE_URL}")
    session, csrftoken = login_session()
    headers = api_headers(csrftoken)
    project_id = ensure_project(session, csrftoken)

    print("Fetching all tasks...")
    tasks = fetch_all_tasks(session, headers, project_id)
    print(f"Total tasks: {len(tasks)}")

    to_delete = set()

    from collections import defaultdict

    # ── 1. Flag signature-only tasks ─────────────────────────────────────────
    for task in tasks:
        code = task.get("data", {}).get("code", "")
        if is_signature_only(code):
            to_delete.add(task["id"])

    print(f"Signature-only (to remove): {len(to_delete)}")

    # ── 2. Deduplicate by query — keep best, delete rest ─────────────────────
    by_query = defaultdict(list)
    for task in tasks:
        query = task.get("data", {}).get("query", "").strip()
        if query:
            by_query[query].append(task)

    dup_q = 0
    for group in by_query.values():
        if len(group) <= 1:
            continue
        group.sort(key=task_score, reverse=True)
        for task in group[1:]:
            if task["id"] not in to_delete:
                to_delete.add(task["id"])
                dup_q += 1

    print(f"Duplicate queries  (to remove): {dup_q}")

    # ── 3. Deduplicate by code body — keep best, delete rest ─────────────────
    by_code = defaultdict(list)
    for task in tasks:
        if task["id"] in to_delete:
            continue
        code = task.get("data", {}).get("code", "").strip()
        if code:
            by_code[code].append(task)

    dup_c = 0
    for group in by_code.values():
        if len(group) <= 1:
            continue
        group.sort(key=task_score, reverse=True)
        for task in group[1:]:
            if task["id"] not in to_delete:
                to_delete.add(task["id"])
                dup_c += 1

    print(f"Duplicate code     (to remove): {dup_c}")
    print(f"Total to delete: {len(to_delete)}")

    if not to_delete:
        print("Nothing to delete.")
        return

    # ── 3. Delete ─────────────────────────────────────────────────────────────
    deleted = failed = 0
    for task_id in to_delete:
        if delete_task(session, headers, task_id):
            deleted += 1
        else:
            failed += 1

    print(f"Deleted {deleted} tasks ({failed} failed)")
    print(f"Remaining tasks: {len(tasks) - deleted}")


if __name__ == "__main__":
    main()
