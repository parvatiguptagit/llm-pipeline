"""
Migrate existing Label Studio tasks to natural-language semantic query format.

Fetches every task from the project, derives a new `query` value from the
stored `hard_query` (raw function name), and PATCHes the task in place.

Usage:
    # Against beta (default):
    python scripts/migrate_query_format.py

    # Against localhost:
    LABEL_STUDIO_URL=http://localhost:8080 python scripts/migrate_query_format.py
"""
import os
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

_VERB_MAP = {
    "get": "retrieve", "calc": "calculate", "del": "delete", "rm": "remove",
    "chk": "check", "init": "initialize", "fmt": "format", "gen": "generate",
    "val": "validate", "upd": "update", "proc": "process", "crt": "create",
    "lst": "list", "cnt": "count", "agg": "aggregate", "auth": "authenticate",
    "cfg": "configure", "conv": "convert", "trns": "transform", "comp": "compute",
    "find": "find", "send": "send", "load": "load", "save": "save",
    "parse": "parse", "build": "build", "fetch": "fetch", "filter": "filter",
    "sort": "sort", "merge": "merge", "split": "split", "read": "read",
    "write": "write", "set": "set",
}


import ast as _ast

def _extract_docstring(code):
    try:
        tree = _ast.parse(code)
        for node in _ast.walk(tree):
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                if (node.body and
                        isinstance(node.body[0], _ast.Expr) and
                        isinstance(node.body[0].value, _ast.Constant) and
                        isinstance(node.body[0].value.value, str)):
                    first_line = node.body[0].value.value.strip().splitlines()[0].strip()
                    if len(first_line) > 8:
                        return first_line.rstrip(".")
    except Exception:
        pass
    return None

def _split_name(func_name):
    s = re.sub(r"([a-z])([A-Z])", r"\1_\2", func_name)
    return [w.lower() for w in re.split(r"[_\s]+", s) if w]


def _conjugate(verb):
    if verb.endswith(("s", "x", "z", "ch", "sh")):
        return verb + "es"
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
        return verb[:-1] + "ies"
    if verb.endswith("e"):
        return verb + "s"
    return verb + "s"


def make_natural_query(func_name, code=None):
    if code:
        doc = _extract_docstring(code)
        if doc:
            doc = doc[0].lower() + doc[1:]
            return f"Where is the function that {doc}?" if not doc.endswith("?") else doc
    words = _split_name(func_name)
    if not words:
        return func_name
    words[0] = _VERB_MAP.get(words[0], words[0])
    verb = _conjugate(words[0])
    rest = " ".join(words[1:])
    if rest:
        return f"Where is the function defined that {verb} {rest}?"
    return f"Where is the {words[0]} function defined?"


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


def migrate():
    print(f"Target: {BASE_URL}")
    session, csrftoken = login_session()
    headers = api_headers(csrftoken)
    project_id = ensure_project(session, csrftoken)

    print("Fetching tasks...")
    tasks = fetch_all_tasks(session, csrftoken, project_id)
    print(f"Found {len(tasks)} tasks")

    updated = skipped = 0
    for task in tasks:
        data = task.get("data", {})
        hard_query = data.get("hard_query") or data.get("query", "")
        if not hard_query:
            skipped += 1
            continue

        new_query = make_natural_query(hard_query, data.get("code", ""))
        if new_query == data.get("query"):
            skipped += 1
            continue

        url = f"{BASE_URL}/api/tasks/{task['id']}/"
        res = session.patch(
            url,
            json={"data": {**data, "query": new_query}},
            headers=headers,
            timeout=60,
        )
        if res.status_code not in (200, 201):
            print(f"  WARN task {task['id']}: {res.status_code} {res.text[:100]}")
        else:
            updated += 1

    print(f"Done — updated {updated}, skipped {skipped} (already correct or no hard_query)")


if __name__ == "__main__":
    migrate()
