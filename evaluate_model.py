import glob
import json
import os
import sys

from sentence_transformers import SentenceTransformer, util

TEST_FILE = os.environ.get("EVAL_TEST_FILE", "data/test_dataset.json")
PASS_THRESHOLD = float(os.environ.get("EVAL_PASS_THRESHOLD", "0.70"))


def _find_latest_model(models_dir="models"):
    matches = sorted(glob.glob(os.path.join(models_dir, "nomic-retrieval-run-*")))
    return matches[-1] if matches else models_dir


MODEL_PATH = os.environ.get("NOMIC_MODEL_DIR") or _find_latest_model()

if not os.path.exists(TEST_FILE):
    print(f"No test file found at {TEST_FILE}. Skipping evaluation.")
    sys.exit(0)

model = SentenceTransformer(MODEL_PATH)

with open(TEST_FILE, "r", encoding="utf-8") as f:
    test_data = json.load(f)

if not test_data:
    print("Test dataset is empty. Skipping evaluation.")
    sys.exit(0)

scores = []
for sample in test_data:
    q_emb = model.encode(sample["query"], convert_to_tensor=True)
    c_emb = model.encode(sample["code"], convert_to_tensor=True)
    scores.append(util.cos_sim(q_emb, c_emb).item())

avg_score = sum(scores) / len(scores)
print(f"Samples evaluated:      {len(scores)}")
print(f"Average similarity:     {avg_score:.4f}")
print(f"Pass threshold:         {PASS_THRESHOLD:.4f}")

if avg_score >= PASS_THRESHOLD:
    print("PASS — model meets quality gate.")
else:
    print("FAIL — model did not meet quality gate.")
    sys.exit(1)
