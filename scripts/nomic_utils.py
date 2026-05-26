"""Nomic Embed helpers for query ↔ code retrieval."""
import os
from pathlib import Path

import torch

NOMIC_MODEL = os.getenv("NOMIC_MODEL", "nomic-ai/nomic-embed-text-v1.5")
MODEL_DIR = Path(os.getenv("NOMIC_MODEL_DIR", "models/nomic-retrieval"))
QUERY_PREFIX = os.getenv("NOMIC_QUERY_PREFIX", "search_query: ")
DOC_PREFIX = os.getenv("NOMIC_DOC_PREFIX", "search_document: ")


def pair_key(query: str, code: str) -> tuple:
    return (query.strip(), code.strip())


def item_query(item: dict) -> str:
    return (
        item.get("query")
        or item.get("hard_query")
        or item.get("soft_query")
        or ""
    ).strip()


def prefix_query(text: str) -> str:
    text = text.strip()
    if text.startswith(QUERY_PREFIX.strip()):
        return text
    return f"{QUERY_PREFIX}{text}"


def prefix_code(text: str) -> str:
    text = text.strip()
    if text.startswith(DOC_PREFIX.strip()):
        return text
    return f"{DOC_PREFIX}{text}"


def load_sentence_model():
    from sentence_transformers import SentenceTransformer

    if MODEL_DIR.exists() and any(MODEL_DIR.iterdir()):
        print(f"Loading fine-tuned Nomic from {MODEL_DIR}")
        return SentenceTransformer(str(MODEL_DIR))
    print(f"Loading base Nomic: {NOMIC_MODEL}")
    return SentenceTransformer(NOMIC_MODEL, trust_remote_code=True)


def encode_queries(model, texts, batch_size=32):
    return model.encode(
        [prefix_query(t) for t in texts],
        convert_to_tensor=True,
        batch_size=batch_size,
        show_progress_bar=False,
    )


def encode_codes(model, texts, batch_size=32):
    return model.encode(
        [prefix_code(t) for t in texts],
        convert_to_tensor=True,
        batch_size=batch_size,
        show_progress_bar=False,
    )


def similarity_scores(model, queries, codes, batch_size=32):
    from sentence_transformers import util

    q_emb = encode_queries(model, queries, batch_size=batch_size)
    c_emb = encode_codes(model, codes, batch_size=batch_size)
    return util.cos_sim(q_emb, c_emb).diagonal().cpu().tolist()


def save_model(model):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    # Windows may keep safetensors files memory-mapped; avoid safe_serialization to prevent file-lock errors.
    model.save(str(MODEL_DIR), safe_serialization=False)
    print(f"Saved Nomic model to {MODEL_DIR}")


def trainable_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")
