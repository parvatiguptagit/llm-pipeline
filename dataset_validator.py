import json
import os

INPUT_FILE = os.environ.get("VALIDATOR_INPUT", "final_train.json")
OUTPUT_FILE = "data/validated_dataset.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

validated = []
seen = set()

for sample in data:
    query = sample.get("query", "").strip()
    code = sample.get("code", "").strip()

    if not query or not code:
        continue

    key = (query, code)
    if key in seen:
        continue

    seen.add(key)
    validated.append(sample)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(validated, f, indent=2)

print(f"Input samples:     {len(data)}")
print(f"Validated samples: {len(validated)}")
print(f"Dropped (dupes/empty): {len(data) - len(validated)}")
