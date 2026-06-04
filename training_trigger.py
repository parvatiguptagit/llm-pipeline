import json
import subprocess

LABEL_FILE = "train.json"
MIN_NEW_LABELS = 20

with open(LABEL_FILE, "r", encoding="utf-8") as f:
    labels = json.load(f)

if len(labels) >= MIN_NEW_LABELS:
    print(f"Threshold reached ({len(labels)} labels). Starting retraining...")
    subprocess.run(["python", "training_pipeline.py"])
else:
    print(f"Not enough labels yet ({len(labels)}/{MIN_NEW_LABELS}). Skipping retraining.")
