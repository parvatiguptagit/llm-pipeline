import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from label_studio_client import (
    BASE_URL,
    api_headers,
    delete_project,
    ensure_project,
    load_project_id,
    login_session,
    parse_results,
    save_project_id,
)
from nomic_utils import pair_key

INPUT = "data/processed/cleaned.json"
MAX_SAMPLES = int(os.getenv("MAX_UPLOAD_SAMPLES", "500"))
RECREATE = os.getenv("RECREATE_LABEL_PROJECT", "0") == "1"
IMPORT_BATCH = int(os.getenv("LS_IMPORT_BATCH", "100"))


def existing_task_keys(session, csrftoken, project_id):
    headers = api_headers(csrftoken)
    keys = set()
    page = 1
    while True:
        url = f"{BASE_URL}/api/tasks/?project={project_id}&page={page}&page_size=100"
        res = session.get(url, headers=headers, timeout=120)
        if res.status_code != 200:
            break
        batch = parse_results(res.json())
        if not batch:
            break
        for task in batch:
            d = task.get("data", {})
            keys.add(pair_key(d.get("query", ""), d.get("code", "")))
        if len(batch) < 100:
            break
        page += 1
    return keys


def upload_to_labelstudio():
    session, csrftoken = login_session()
    headers = api_headers(csrftoken)

    if RECREATE:
        old_id = load_project_id()
        if old_id:
            delete_project(session, csrftoken, old_id)
        save_project_id("")
        project_id = ensure_project(session, csrftoken)
    else:
        project_id = ensure_project(session, csrftoken)

    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    data = data[:MAX_SAMPLES]
    known = existing_task_keys(session, csrftoken, project_id)

    tasks = []
    for item in data:
        query = item.get("query") or item.get("hard_query") or item.get("soft_query", "")
        code = item.get("code", "")
        if not query or not code:
            continue
        key = pair_key(query, code)
        if key in known:
            continue
        tasks.append({"data": {"query": query, "code": code}})

    if not tasks:
        print("No new tasks to upload (project unchanged)")
        return

    print(f"Uploading {len(tasks)} new tasks to project {project_id}")

    url = f"{BASE_URL}/api/projects/{project_id}/import"
    uploaded = 0
    for start in range(0, len(tasks), IMPORT_BATCH):
        chunk = tasks[start : start + IMPORT_BATCH]
        res = session.post(url, json=chunk, headers=headers, timeout=120)
        if res.status_code not in (200, 201):
            raise RuntimeError(f"Upload failed: {res.status_code} {res.text[:300]}")
        uploaded += len(chunk)

    print(f"Uploaded {uploaded} tasks (total requested {len(tasks)})")


if __name__ == "__main__":
    upload_to_labelstudio()
