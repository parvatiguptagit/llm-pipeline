"""Semi-supervised pseudo-labels with Nomic Embed — uploads tasks and annotations to Label Studio."""
import json
import os
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
from nomic_utils import item_query, load_sentence_model, pair_key, similarity_scores

INPUT = "data/processed/cleaned.json"
HUMAN = "train.json"
MAX_UPLOAD = int(os.getenv("MAX_UPLOAD_SAMPLES", "500"))
MAX_AUTO = int(os.getenv("MAX_AUTO_SAMPLES", "100000"))
PSEUDO_HIGH = float(os.getenv("PSEUDO_HIGH", "0.65"))
PSEUDO_LOW = float(os.getenv("PSEUDO_LOW", "0.45"))
BATCH_SIZE = int(os.getenv("NOMIC_BATCH_SIZE", "64"))
IMPORT_BATCH = int(os.getenv("LS_IMPORT_BATCH", "100"))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def existing_task_keys(session, csrftoken, project_id):
    """Return (pair_key → task_id) for all tasks already in the project."""
    headers = api_headers(csrftoken)
    mapping = {}
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
            key = pair_key(d.get("query", ""), d.get("code", ""))
            mapping[key] = task["id"]
        if len(batch) < 100:
            break
        page += 1
    return mapping


def upload_tasks(session, csrftoken, project_id, tasks):
    """Upload new tasks in batches, return {pair_key: task_id} for uploaded."""
    headers = api_headers(csrftoken)
    url = f"{BASE_URL}/api/projects/{project_id}/import"
    id_map = {}
    total = len(tasks)
    for start in range(0, total, IMPORT_BATCH):
        chunk = tasks[start : start + IMPORT_BATCH]
        res = session.post(url, json=[t["payload"] for t in chunk], headers=headers, timeout=120)
        if res.status_code not in (200, 201):
            raise RuntimeError(f"Task upload failed: {res.status_code} {res.text[:300]}")
        for t in chunk:
            id_map[t["key"]] = None
        print(f"  uploaded {min(start + IMPORT_BATCH, total)}/{total} tasks...")
    return id_map


def resolve_task_ids(session, csrftoken, project_id, keys_needed):
    """Fetch tasks until all keys in keys_needed are found, return {key: task_id}."""
    headers = api_headers(csrftoken)
    mapping = {}
    page = 1
    while len(mapping) < len(keys_needed):
        url = f"{BASE_URL}/api/tasks/?project={project_id}&page={page}&page_size=100"
        res = session.get(url, headers=headers, timeout=120)
        if res.status_code != 200:
            break
        batch = parse_results(res.json())
        if not batch:
            break
        for task in batch:
            d = task.get("data", {})
            key = pair_key(d.get("query", ""), d.get("code", ""))
            if key in keys_needed:
                mapping[key] = task["id"]
        if len(batch) < 100:
            break
        page += 1
    return mapping


def push_annotation(session, csrftoken, task_id, choice):
    headers = api_headers(csrftoken)
    payload = {
        "result": [
            {
                "from_name": "label",
                "to_name": "code",
                "type": "choices",
                "value": {"choices": [choice]},
            }
        ],
        "was_cancelled": False,
        "ground_truth": False,
    }
    res = session.post(
        f"{BASE_URL}/api/tasks/{task_id}/annotations/",
        json=payload,
        headers=headers,
        timeout=60,
    )
    return res.status_code in (200, 201)


def main():
    all_data = load_json(INPUT)
    human = load_json(HUMAN) if os.path.exists(HUMAN) else []

    human_keys = {pair_key(item_query(item), item.get("code", "")) for item in human}

    candidates = []
    for item in all_data:
        query = item_query(item)
        code = item.get("code", "")
        key = pair_key(query, code)
        if key not in human_keys and query and code:
            candidates.append({"query": query, "code": code, "key": key})

    if not candidates:
        print("Auto-labeled 0 samples (all covered by human labels or empty pool)")
        return

    # Connect to Label Studio
    session, csrftoken = login_session()
    project_id = ensure_project(session, csrftoken)
    existing = existing_task_keys(session, csrftoken, project_id)

    # Upload any candidates not yet in Label Studio
    new_tasks = [
        {"payload": {"data": {"query": c["query"], "code": c["code"]}}, "key": c["key"]}
        for c in candidates
        if c["key"] not in existing
    ][:MAX_UPLOAD]

    if new_tasks:
        print(f"Uploading {len(new_tasks)} new tasks to Label Studio (capped at MAX_UPLOAD_SAMPLES={MAX_UPLOAD})...")
        upload_tasks(session, csrftoken, project_id, new_tasks)
        print("Upload done. Fetching task IDs...")
        new_keys = {t["key"] for t in new_tasks}
        resolved = resolve_task_ids(session, csrftoken, project_id, new_keys)
        existing.update(resolved)

    # Score all candidates and push annotations for high/low confidence
    model = load_sentence_model()
    annotated = skipped = 0

    for start in range(0, len(candidates), BATCH_SIZE):
        if annotated >= MAX_AUTO:
            break
        batch = candidates[start : start + BATCH_SIZE]
        queries = [c["query"] for c in batch]
        codes = [c["code"] for c in batch]
        scores = similarity_scores(model, queries, codes, batch_size=BATCH_SIZE)

        for item, score in zip(batch, scores):
            if score >= PSEUDO_HIGH:
                choice = "Relevant"
            elif score <= PSEUDO_LOW:
                choice = "Not Relevant"
            else:
                skipped += 1
                continue

            task_id = existing.get(item["key"])
            if not task_id:
                skipped += 1
                continue

            if push_annotation(session, csrftoken, task_id, choice):
                annotated += 1

            if annotated >= MAX_AUTO:
                break

    print(
        f"Pushed {annotated} auto-annotations to Label Studio "
        f"(skipped uncertain band {PSEUDO_LOW}–{PSEUDO_HIGH}: {skipped} pairs)"
    )


if __name__ == "__main__":
    main()
