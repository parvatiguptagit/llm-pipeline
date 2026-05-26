import json
import os
import re

INPUT_DIR = "data/raw/repo"
OUTPUT = "data/processed/functions.json"

# (extension, regex, group for name) — multi-language function/method signatures
PATTERNS = [
    (".py", re.compile(r"^\s*def\s+([a-zA-Z_][\w]*)\s*\("), 1),
    (".java", re.compile(r"^\s*(?:public|private|protected|static|\s)+[\w<>\[\],\s]+\s+([a-zA-Z_][\w]*)\s*\("), 1),
    (".kt", re.compile(r"^\s*fun\s+([a-zA-Z_][\w]*)\s*\("), 1),
    (".go", re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?([a-zA-Z_][\w]*)\s*\("), 1),
    (".rs", re.compile(r"^\s*(?:pub\s+)?fn\s+([a-zA-Z_][\w]*)\s*[\(<]"), 1),
    (".js", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)\s*\("), 1),
    (".ts", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)\s*\("), 1),
    (".jsx", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)\s*\("), 1),
    (".tsx", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)\s*\("), 1),
    (".cs", re.compile(r"^\s*(?:public|private|protected|internal|static|\s)+[\w<>\[\],\s]+\s+([a-zA-Z_][\w]*)\s*\("), 1),
    (".cpp", re.compile(r"^\s*[\w:*&<>\s]+\s+([a-zA-Z_][\w]*)\s*\([^;]*\)\s*(?:const)?\s*\{?\s*$"), 1),
    (".c", re.compile(r"^\s*[\w:*&\s]+\s+([a-zA-Z_][\w]*)\s*\([^;]*\)\s*\{?\s*$"), 1),
    (".rb", re.compile(r"^\s*def\s+([a-zA-Z_][\w]*[!?=]?)\s*"), 1),
    (".php", re.compile(r"^\s*(?:public|private|protected|static|\s)*function\s+([a-zA-Z_][\w]*)\s*\("), 1),
    (".scala", re.compile(r"^\s*def\s+([a-zA-Z_][\w]*)\s*[\(:]"), 1),
]

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", "target"}


def extract_from_file(path, pattern, name_group):
    rows = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = pattern.match(line)
                if not m:
                    continue
                name = m.group(name_group)
                if name in ("if", "for", "while", "switch", "catch"):
                    continue
                rows.append({"query": name, "code": line.strip()})
    except OSError:
        pass
    return rows


def main():
    data = []
    seen = set()

    for root, dirs, files in os.walk(INPUT_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            path = os.path.join(root, file)
            for ext, pattern, group in PATTERNS:
                if not file.endswith(ext):
                    continue
                for row in extract_from_file(path, pattern, group):
                    key = (row["query"], row["code"])
                    if key in seen:
                        continue
                    seen.add(key)
                    data.append(row)
                break

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Extracted {len(data)} functions (multi-language)")


if __name__ == "__main__":
    main()
