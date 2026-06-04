import glob
import json
import os
import sys

from sentence_transformers import SentenceTransformer, util

INPUT_FILE = "data/processed/functions.json"
AUTO_LABEL_FILE = "data/auto_labels.json"
HUMAN_REVIEW_FILE = "data/human_review.json"
REJECTED_FILE = "data/rejected.json"

HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.70


def _find_latest_model(models_dir="models"):
    matches = sorted(glob.glob(os.path.join(models_dir, "nomic-retrieval-run-*")))
    return matches[-1] if matches else models_dir


MODEL_PATH = os.environ.get("NOMIC_MODEL_DIR") or _find_latest_model()

if not os.path.exists(INPUT_FILE):
    print(f"Input file not found: {INPUT_FILE}")
    print("Run pipeline.py (Step 1) first to generate extracted_functions.json")
    sys.exit(0)

model = SentenceTransformer(MODEL_PATH)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    samples = json.load(f)

auto_labels = []
human_review = []
rejected = []

for sample in samples:
    query = sample["query"]
    code = sample["code"]

    query_embedding = model.encode(query, convert_to_tensor=True)
    code_embedding = model.encode(code, convert_to_tensor=True)

    similarity = util.cos_sim(query_embedding, code_embedding).item()

    sample["confidence"] = similarity

    if similarity >= HIGH_CONFIDENCE:
        sample["label"] = "Relevant"
        auto_labels.append(sample)
    elif similarity >= MEDIUM_CONFIDENCE:
        human_review.append(sample)
    else:
        rejected.append(sample)

with open(AUTO_LABEL_FILE, "w", encoding="utf-8") as f:
    json.dump(auto_labels, f, indent=2)

with open(HUMAN_REVIEW_FILE, "w", encoding="utf-8") as f:
    json.dump(human_review, f, indent=2)

with open(REJECTED_FILE, "w", encoding="utf-8") as f:
    json.dump(rejected, f, indent=2)

print(f"Auto labeled:  {len(auto_labels)}")
print(f"Human review:  {len(human_review)}")
print(f"Rejected:      {len(rejected)}")
