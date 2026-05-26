"""Semi-supervised pseudo-labels with Nomic Embed (batched for large pools)."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nomic_utils import item_query, load_sentence_model, pair_key, similarity_scores

INPUT = "data/processed/cleaned.json"
HUMAN = "train.json"
OUTPUT = "auto.json"
MAX_AUTO = int(os.getenv("MAX_AUTO_SAMPLES", "100000"))
PSEUDO_HIGH = float(os.getenv("PSEUDO_HIGH", "0.55"))
PSEUDO_LOW = float(os.getenv("PSEUDO_LOW", "0.45"))
BATCH_SIZE = int(os.getenv("NOMIC_BATCH_SIZE", "64"))


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
            candidates.append({"query": query, "code": code})

    if not candidates:
        with open(OUTPUT, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        print("Auto-labeled 0 samples (all covered by human labels or empty pool)")
        return

    model = load_sentence_model()
    auto = []

    for start in range(0, len(candidates), BATCH_SIZE):
        if len(auto) >= MAX_AUTO:
            break
        batch = candidates[start : start + BATCH_SIZE]
        queries = [c["query"] for c in batch]
        codes = [c["code"] for c in batch]
        scores = similarity_scores(model, queries, codes, batch_size=BATCH_SIZE)

        for item, score in zip(batch, scores):
            if score >= PSEUDO_HIGH:
                label = 1
            elif score <= PSEUDO_LOW:
                label = 0
            else:
                continue
            auto.append(
                {
                    "query": item["query"],
                    "code": item["code"],
                    "label": label,
                    "source": "pseudo",
                    "confidence": round(float(score), 4),
                }
            )
            if len(auto) >= MAX_AUTO:
                break

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(auto, f, indent=2)

    print(f"Nomic pseudo-labeled {len(auto)} samples (skipped uncertain band {PSEUDO_LOW}-{PSEUDO_HIGH})")


if __name__ == "__main__":
    main()
