"""Push Nomic Relevant / Not Relevant pre-annotations to Label Studio tasks."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from label_studio_client import (
    BASE_URL,
    api_headers,
    ensure_project,
    load_project_id,
    login_session,
    parse_results,
)
from nomic_utils import load_sentence_model, similarity_scores

MAX_PREDICTIONS = int(os.getenv("MAX_PREDICTIONS", "2000"))
BATCH_SIZE = int(os.getenv("NOMIC_BATCH_SIZE", "64"))
PUSH = os.getenv("PUSH_PREDICTIONS", "1") == "1"


def choice_from_score(score: float) -> tuple[str, float]:
    if score >= 0.5:
        return "Relevant", float(score)
    return "Not Relevant", float(1.0 - score)


def fetch_tasks(session, csrftoken, project_id):
    headers = api_headers(csrftoken)
    page = 1
    tasks = []
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


def main():
    if not PUSH:
        print("PUSH_PREDICTIONS=0, skipping")
        return

    project_id = load_project_id()
    if not project_id:
        print("No project_id.txt; run pipeline upload first.")
        return

    session, csrftoken = login_session()
    ensure_project(session, csrftoken)
    tasks = fetch_tasks(session, csrftoken, project_id)

    # Unlabeled tasks only
    targets = []
    for task in tasks:
        if task.get("annotations"):
            continue
        data = task.get("data", {})
        query = data.get("query", "")
        code = data.get("code", "")
        if query and code:
            targets.append(task)
        if len(targets) >= MAX_PREDICTIONS:
            break

    if not targets:
        print("No tasks need predictions")
        return

    model = load_sentence_model()
    headers = api_headers(csrftoken)
    pushed = 0

    for start in range(0, len(targets), BATCH_SIZE):
        batch = targets[start : start + BATCH_SIZE]
        queries = [t["data"].get("query", "") for t in batch]
        codes = [t["data"].get("code", "") for t in batch]
        scores = similarity_scores(model, queries, codes, batch_size=BATCH_SIZE)

        for task, score in zip(batch, scores):
            choice, conf = choice_from_score(score)
            payload = {
                "task": task["id"],
                "result": [
                    {
                        "from_name": "label",
                        "to_name": "code",
                        "type": "choices",
                        "value": {"choices": [choice]},
                    }
                ],
                "score": conf,
                "model_version": "nomic-retrieval",
            }
            res = session.post(
                f"{BASE_URL}/api/predictions",
                json=payload,
                headers=headers,
                timeout=60,
            )
            if res.status_code in (200, 201):
                pushed += 1

    print(f"Pushed {pushed} predictions to Label Studio")


if __name__ == "__main__":
    main()
