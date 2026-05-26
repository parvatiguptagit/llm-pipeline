"""Fine-tune Nomic Embed for query↔code relevance using supervised + semi labels."""

import json
import os
import sys
from pathlib import Path

from torch.utils.data import DataLoader
from sentence_transformers import InputExample
from sentence_transformers.losses import CosineSimilarityLoss

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nomic_utils import load_sentence_model, prefix_code, prefix_query, save_model

EPOCHS = int(os.getenv("TRAIN_EPOCHS", "2"))
MAX_SAMPLES = int(os.getenv("MAX_TRAIN_SAMPLES", "50000"))
BATCH_SIZE = int(os.getenv("TRAIN_BATCH_SIZE", "16"))
LR = float(os.getenv("TRAIN_LR", "2e-5"))
INPUT = os.getenv("TRAIN_INPUT", "final_train.json")


def train():
    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        print("No training samples; skipping Nomic fine-tune.")
        return

    data = data[:MAX_SAMPLES]
    model = load_sentence_model()

    examples = []
    for item in data:
        query = item.get("query", "") or item.get("hard_query", "") or item.get("soft_query", "")
        code = item.get("code", "")
        if not query or not code:
            continue
        label = float(item.get("label", 0))
        examples.append(
            InputExample(
                texts=[prefix_query(query), prefix_code(code)],
                label=label,
            )
        )

    if not examples:
        print("No valid (query, code, label) examples; skipping fine-tune.")
        return

    print(f"Nomic training: {len(examples)} samples, {EPOCHS} epoch(s).")

    train_dataloader = DataLoader(examples, shuffle=True, batch_size=BATCH_SIZE)
    train_loss = CosineSimilarityLoss(model)

    # warmup_steps default (10000) is too high for small runs; set to 0.
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=EPOCHS,
        warmup_steps=0,
        optimizer_params={"lr": LR},
        show_progress_bar=True,
    )

    save_model(model)
    print("Nomic training complete")


if __name__ == "__main__":
    train()
