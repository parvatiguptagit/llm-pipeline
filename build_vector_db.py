import glob
import json
import os

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

DATA_FILE = os.environ.get("VECTOR_DATA_FILE", "data/validated_dataset.json")
INDEX_FILE = os.environ.get("VECTOR_INDEX_FILE", "vector.index")


def _find_latest_model(models_dir="models"):
    matches = sorted(glob.glob(os.path.join(models_dir, "nomic-retrieval-run-*")))
    return matches[-1] if matches else models_dir


MODEL_PATH = os.environ.get("NOMIC_MODEL_DIR") or _find_latest_model()

model = SentenceTransformer(MODEL_PATH)

with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

texts = [x["code"] for x in data]

print(f"Encoding {len(texts)} samples...")
embeddings = model.encode(texts, show_progress_bar=True)
embeddings = np.array(embeddings).astype("float32")

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, INDEX_FILE)

print(f"Vector database saved to {INDEX_FILE} ({index.ntotal} vectors, dim={embeddings.shape[1]})")
