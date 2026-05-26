import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nomic_utils import pair_key


def _load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


human = _load("train.json")
auto = _load("auto.json")

for item in human:
    item["source"] = item.get("source", "human")

merged = {}
for item in human:
    key = pair_key(item.get("query", ""), item.get("code", ""))
    merged[key] = item

for item in auto:
    key = pair_key(item.get("query", ""), item.get("code", ""))
    if key not in merged:
        merged[key] = item

final = list(merged.values())
with open("final_train.json", "w", encoding="utf-8") as f:
    json.dump(final, f, indent=2)

print(f"Final dataset: {len(final)} (human={len(human)}, pseudo added={len(final) - len(human)})")
