"""
Fix double-processed queries like:
  'Where is the function defined that as function that mains?'
by re-deriving the query from the function name found in the code body.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from label_studio_client import (
    BASE_URL, api_headers, ensure_project, login_session, parse_results,
)

# ── same logic as clean_data.py ───────────────────────────────────────────────
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

_FUNC_NAME_RES = [
    re.compile(r"def\s+([a-zA-Z_][\w]*)\s*\("),
    re.compile(r"function\s+([a-zA-Z_$][\w$]*)\s*\("),
    re.compile(r"fun\s+([a-zA-Z_][\w]*)\s*\("),
    re.compile(r"func\s+(?:\([^)]+\)\s+)?([a-zA-Z_][\w]*)\s*\("),
    re.compile(r"fn\s+([a-zA-Z_][\w]*)\s*[\(<]"),
]


def func_name_from_code(code):
    first_line = code.strip().splitlines()[0] if code.strip() else ""
    for pat in _FUNC_NAME_RES:
        m = pat.search(first_line)
        if m:
            return m.group(1)
    return None


def _split_name(name):
    s = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    return [w.lower() for w in re.split(r"[_\s]+", s) if w]


def _conjugate(verb):
    if verb.endswith(("s", "x", "z", "ch", "sh")):
        return verb + "es"
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
        return verb[:-1] + "ies"
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


def is_garbled(query):
    return "as function that" in query.lower()


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


def main():
    print(f"Target: {BASE_URL}")
    session, csrftoken = login_session()
    headers = api_headers(csrftoken)
    project_id = ensure_project(session, csrftoken)

    print("Fetching tasks...")
    tasks = fetch_all_tasks(session, headers, project_id)
    garbled = [t for t in tasks if is_garbled(t["data"].get("query", ""))]
    print(f"Found {len(garbled)} garbled tasks out of {len(tasks)}")

    fixed = skipped = 0
    for task in garbled:
        data = task["data"]
        code = data.get("code", "")
        func_name = func_name_from_code(code)
        if not func_name:
            skipped += 1
            continue

        new_query = make_natural_query(func_name, code)
        url = f"{BASE_URL}/api/tasks/{task['id']}/"
        res = session.patch(
            url,
            json={"data": {**data, "query": new_query}},
            headers=headers,
            timeout=60,
        )
        if res.status_code in (200, 201):
            fixed += 1
        else:
            print(f"  WARN task {task['id']}: {res.status_code} {res.text[:100]}")
            skipped += 1

    print(f"Done — fixed {fixed}, skipped {skipped}")


if __name__ == "__main__":
    main()
