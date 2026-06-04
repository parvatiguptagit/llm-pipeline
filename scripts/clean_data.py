import ast
import json
import re

INPUT = "data/processed/functions.json"
OUTPUT = "data/processed/cleaned.json"

# Maps common short verbs to their full natural-language equivalents
_VERB_MAP = {
    "get": "retrieve",
    "calc": "calculate",
    "del": "delete",
    "rm": "remove",
    "chk": "check",
    "init": "initialize",
    "fmt": "format",
    "gen": "generate",
    "val": "validate",
    "upd": "update",
    "proc": "process",
    "crt": "create",
    "lst": "list",
    "cnt": "count",
    "agg": "aggregate",
    "auth": "authenticate",
    "cfg": "configure",
    "conv": "convert",
    "trns": "transform",
    "comp": "compute",
    "find": "find",
    "send": "send",
    "load": "load",
    "save": "save",
    "parse": "parse",
    "build": "build",
    "fetch": "fetch",
    "filter": "filter",
    "sort": "sort",
    "merge": "merge",
    "split": "split",
    "read": "read",
    "write": "write",
    "set": "set",
}

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

def _extract_docstring(code):
    """Return the first line of the docstring from a Python function, or None."""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if (node.body and
                        isinstance(node.body[0], ast.Expr) and
                        isinstance(node.body[0].value, ast.Constant) and
                        isinstance(node.body[0].value.value, str)):
                    first_line = node.body[0].value.value.strip().splitlines()[0].strip()
                    if len(first_line) > 8:
                        return first_line.rstrip(".")
    except Exception:
        pass
    return None

def make_natural_query(func_name, code=None):
    """Build a natural-language semantic search question.

    Prefers the docstring (semantically accurate) over the function name.
    """
    if code:
        doc = _extract_docstring(code)
        if doc:
            doc = doc[0].lower() + doc[1:]  # lowercase first char
            if doc.endswith("?"):
                return doc
            return f"Where is the function that {doc}?"

    words = _split_name(func_name)
    if not words:
        return func_name
    words[0] = _VERB_MAP.get(words[0], words[0])
    verb = _conjugate(words[0])
    rest = " ".join(words[1:])
    if rest:
        return f"Where is the function defined that {verb} {rest}?"
    return f"Where is the {words[0]} function defined?"

def make_soft_query(func_name):
    words = _split_name(func_name)
    if not words:
        return func_name
    words[0] = _VERB_MAP.get(words[0], words[0])
    return " ".join(words)

def main():
    with open(INPUT) as f:
        data = json.load(f)

    seen = set()
    cleaned = []

    for item in data:
        code = item["code"]

        if code in seen:
            continue
        seen.add(code)

        func_name = item["query"]
        natural = make_natural_query(func_name, code)

        cleaned.append({
            "query": natural,
            "hard_query": func_name,
            "soft_query": make_soft_query(func_name),
            "code": code,
            "instruction": f"Write a Python function that {make_soft_query(func_name)}",
        })

    with open(OUTPUT, "w") as f:
        json.dump(cleaned, f, indent=2)

    print(f"Enhanced dataset: {len(cleaned)} samples")

if __name__ == "__main__":
    main()