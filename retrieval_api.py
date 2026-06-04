import glob
import json
import os

import faiss
import numpy as np
from fastapi import FastAPI, HTTPException
from sentence_transformers import SentenceTransformer

DATA_FILE = os.environ.get("VECTOR_DATA_FILE", "data/validated_dataset.json")
INDEX_FILE = os.environ.get("VECTOR_INDEX_FILE", "vector.index")
TOP_K = int(os.environ.get("RETRIEVAL_TOP_K", "5"))


def _find_latest_model(models_dir="models"):
    matches = sorted(glob.glob(os.path.join(models_dir, "nomic-retrieval-run-*")))
    return matches[-1] if matches else models_dir


MODEL_PATH = os.environ.get("NOMIC_MODEL_DIR") or _find_latest_model()

app = FastAPI(title="Code Retrieval API")

# Loaded lazily on first request so the server starts even before the index is built
_model = None
_index = None
_data = None


def _load():
    global _model, _index, _data
    if _model is not None:
        return

    if not os.path.exists(INDEX_FILE):
        raise HTTPException(
            status_code=503,
            detail=f"Vector index not built yet. Run: python build_vector_db.py",
        )
    if not os.path.exists(DATA_FILE):
        raise HTTPException(
            status_code=503,
            detail=f"Dataset not found: {DATA_FILE}. Run the full pipeline first.",
        )

    _model = SentenceTransformer(MODEL_PATH)
    _index = faiss.read_index(INDEX_FILE)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        _data = json.load(f)


@app.post("/search")
def search(payload: dict):
    _load()
    query = payload.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query field is required")

    top_k = int(payload.get("top_k", TOP_K))

    embedding = _model.encode([query])
    embedding = np.array(embedding).astype("float32")

    distances, indices = _index.search(embedding, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < len(_data):
            result = dict(_data[idx])
            result["distance"] = float(dist)
            results.append(result)

    return {"query": query, "results": results}


@app.get("/health")
def health():
    index_ready = os.path.exists(INDEX_FILE)
    data_ready = os.path.exists(DATA_FILE)
    return {
        "status": "ready" if (index_ready and data_ready) else "not_ready",
        "index_file": INDEX_FILE,
        "index_exists": index_ready,
        "data_file": DATA_FILE,
        "data_exists": data_ready,
        "indexed_samples": _index.ntotal if _index is not None else 0,
    }
