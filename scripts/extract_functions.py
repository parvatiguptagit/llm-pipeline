import json
import os
import re

INPUT_DIR = "data/raw/repo"
OUTPUT = "data/processed/functions.json"

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "target"}
MAX_FUNC_LINES = 150
SKIP_NAMES = {"if", "for", "while", "switch", "catch", "else"}

# ── Python (indentation-based) ────────────────────────────────────────────────
PY_DEF = re.compile(r"^(\s*)def\s+([a-zA-Z_][\w]*)\s*\(")

# ── Brace-based languages ─────────────────────────────────────────────────────
BRACE_PATTERNS = {
    ".java":  re.compile(r"^\s*(?:public|private|protected|static|\s)+[\w<>\[\],\s]+\s+([a-zA-Z_][\w]*)\s*\("),
    ".kt":    re.compile(r"^\s*fun\s+([a-zA-Z_][\w]*)\s*\("),
    ".go":    re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?([a-zA-Z_][\w]*)\s*\("),
    ".rs":    re.compile(r"^\s*(?:pub\s+)?fn\s+([a-zA-Z_][\w]*)\s*[\(<]"),
    ".js":    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)\s*\("),
    ".ts":    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)\s*\("),
    ".jsx":   re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)\s*\("),
    ".tsx":   re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)\s*\("),
    ".cs":    re.compile(r"^\s*(?:public|private|protected|internal|static|\s)+[\w<>\[\],\s]+\s+([a-zA-Z_][\w]*)\s*\("),
    ".cpp":   re.compile(r"^\s*[\w:*&<>\s]+\s+([a-zA-Z_][\w]*)\s*\([^;]*\)\s*(?:const)?\s*\{?\s*$"),
    ".c":     re.compile(r"^\s*[\w:*&\s]+\s+([a-zA-Z_][\w]*)\s*\([^;]*\)\s*\{?\s*$"),
    ".php":   re.compile(r"^\s*(?:public|private|protected|static|\s)*function\s+([a-zA-Z_][\w]*)\s*\("),
    ".scala": re.compile(r"^\s*def\s+([a-zA-Z_][\w]*)\s*[\(:]"),
}

# ── Ruby (end-based) ──────────────────────────────────────────────────────────
RB_DEF   = re.compile(r"^\s*def\s+([a-zA-Z_][\w]*[!?=]?)\s*")
RB_BLOCK = re.compile(r"^\s*(def|do|begin|if|unless|while|until|for|case|module|class)\b")
RB_END   = re.compile(r"^\s*end\s*$")


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.readlines()
    except OSError:
        return []


def extract_python(lines):
    results, i = [], 0
    while i < len(lines):
        m = PY_DEF.match(lines[i])
        if m:
            indent, name = m.group(1), m.group(2)
            if name not in SKIP_NAMES:
                body, j = [lines[i].rstrip()], i + 1

                # Phase 1: collect multi-line signature until parens balance
                paren_depth = lines[i].count("(") - lines[i].count(")")
                while j < len(lines) and paren_depth > 0:
                    line = lines[j]
                    body.append(line.rstrip())
                    paren_depth += line.count("(") - line.count(")")
                    j += 1

                # Phase 2: collect body via indentation
                while j < len(lines):
                    line = lines[j]
                    if line.strip() == "":
                        body.append("")
                        j += 1
                        continue
                    if len(line) - len(line.lstrip()) <= len(indent):
                        break
                    body.append(line.rstrip())
                    j += 1

                if 2 <= len(body) <= MAX_FUNC_LINES:
                    results.append({"query": name, "code": "\n".join(body).strip()})
                i = j
                continue
        i += 1
    return results


def extract_brace(lines, pattern):
    results, i = [], 0
    while i < len(lines):
        m = pattern.match(lines[i])
        if m:
            name = m.group(1)
            if name not in SKIP_NAMES:
                body, brace_count, found_open = [], 0, False
                j = i
                while j < len(lines) and j < i + MAX_FUNC_LINES:
                    line = lines[j]
                    body.append(line.rstrip())
                    brace_count += line.count("{") - line.count("}")
                    if "{" in line:
                        found_open = True
                    if found_open and brace_count <= 0:
                        j += 1
                        break
                    j += 1
                if found_open and len(body) >= 2:
                    results.append({"query": name, "code": "\n".join(body).strip()})
                i = j
                continue
        i += 1
    return results


def extract_ruby(lines):
    results, i = [], 0
    while i < len(lines):
        m = RB_DEF.match(lines[i])
        if m:
            name = m.group(1)
            body, depth, j = [lines[i].rstrip()], 1, i + 1
            while j < len(lines) and j < i + MAX_FUNC_LINES:
                line = lines[j]
                body.append(line.rstrip())
                if RB_BLOCK.match(line):
                    depth += 1
                if RB_END.match(line):
                    depth -= 1
                    if depth <= 0:
                        j += 1
                        break
                j += 1
            if len(body) >= 2:
                results.append({"query": name, "code": "\n".join(body).strip()})
            i = j
            continue
        i += 1
    return results


def extract_from_file(path):
    ext = os.path.splitext(path)[1].lower()
    lines = _read(path)
    if not lines:
        return []
    if ext == ".py":
        return extract_python(lines)
    if ext == ".rb":
        return extract_ruby(lines)
    if ext in BRACE_PATTERNS:
        return extract_brace(lines, BRACE_PATTERNS[ext])
    return []


def main():
    data, seen = [], set()
    for root, dirs, files in os.walk(INPUT_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            path = os.path.join(root, file)
            for row in extract_from_file(path):
                key = (row["query"], row["code"])
                if key in seen:
                    continue
                seen.add(key)
                data.append(row)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Extracted {len(data)} functions (multi-language)")


if __name__ == "__main__":
    main()
