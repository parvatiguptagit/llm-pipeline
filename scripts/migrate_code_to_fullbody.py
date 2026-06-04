"""
Patch Label Studio tasks whose code field is only a function signature
with the full function body from data/processed/cleaned.json.
"""
import json
import re
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

CLEANED = "data/processed/cleaned.json"

_FUNC_NAME_RE = [
    re.compile(r"def\s+([a-zA-Z_][\w]*)\s*\("),
    re.compile(r"function\s+([a-zA-Z_$][\w$]*)\s*\("),
    re.compile(r"fun\s+([a-zA-Z_][\w]*)\s*\("),
    re.compile(r"func\s+(?:\([^)]+\)\s+)?([a-zA-Z_][\w]*)\s*\("),
    re.compile(r"fn\s+([a-zA-Z_][\w]*)\s*[\(<]"),
]


def func_name_from_sig(sig):
    for pat in _FUNC_NAME_RE:
        m = pat.search(sig)
        if m:
            return m.group(1)
    return None


def build_index(cleaned_path):
    """Build name → list of full-body codes from cleaned.json."""
    with open(cleaned_path, encoding="utf-8") as f:
        data = json.load(f)
    index = {}
    for item in data:
        name = item.get("hard_query", "")
        code = item.get("code", "")
        if name and code:
            index.setdefault(name, []).append(code)
    return index


def fetch_all_tasks(session, csrftoken, project_id):
    headers = api_headers(csrftoken)
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


def needs_update(task_code, full_code):
    """True if the cleaned.json version is meaningfully longer (has a real body)."""
    return len(full_code.strip()) > len(task_code.strip()) + 20


def best_match(sig_first_line, candidates):
    sig = sig_first_line.strip()
    for code in candidates:
        if code.strip().splitlines()[0].strip() == sig:
            return code
    return max(candidates, key=len)


def migrate():
    print(f"Target: {BASE_URL}")
    index = build_index(CLEANED)
    print(f"Loaded {sum(len(v) for v in index.values())} full-body entries "
          f"across {len(index)} function names")

    session, csrftoken = login_session()
    headers = api_headers(csrftoken)
    project_id = ensure_project(session, csrftoken)

    print("Fetching tasks...")
    tasks = fetch_all_tasks(session, csrftoken, project_id)
    print(f"Found {len(tasks)} tasks")

    updated = skipped = no_match = 0
    for task in tasks:
        data = task.get("data", {})
        code = data.get("code", "")
        name = func_name_from_sig(code)

        if not name or name not in index:
            no_match += 1
            continue

        first_line = code.strip().splitlines()[0] if code.strip() else ""
        full_code = best_match(first_line, index[name])

        if not needs_update(code, full_code):
            skipped += 1
            continue

        url = f"{BASE_URL}/api/tasks/{task['id']}/"
        res = session.patch(
            url,
            json={"data": {**data, "code": full_code}},
            headers=headers,
            timeout=60,
        )
        if res.status_code not in (200, 201):
            print(f"  WARN task {task['id']}: {res.status_code} {res.text[:100]}")
        else:
            updated += 1

    print(f"Done — updated {updated}, already longest {skipped}, no match {no_match}")


if __name__ == "__main__":
    migrate()
