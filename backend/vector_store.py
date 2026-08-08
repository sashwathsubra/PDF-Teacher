"""
vector_store.py
Manages embeddings and FAISS index per session.
Uses sentence-transformers (all-MiniLM-L6-v2) — free, local, no API needed.
"""

from __future__ import annotations

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Tuple
import os
import json

# ---------------------------------------------------------------------------
# Model — loaded once globally (first load downloads ~90 MB, then cached)
# ---------------------------------------------------------------------------
_MODEL_NAME = "all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"[vector_store] Loading embedding model: {_MODEL_NAME}...")
        _model = SentenceTransformer(_MODEL_NAME)
        print("[vector_store] Model loaded.")
    return _model


def preload_models() -> None:
    """Public helper to force model download/load at build/startup time."""
    _get_model()


# ---------------------------------------------------------------------------
# In-memory session store
# { session_id: { "index": faiss.Index, "metadata": [chunk_dict, ...] } }
# ---------------------------------------------------------------------------
_sessions: Dict[str, Dict[str, Any]] = {}

# Persisted sessions directory (faiss index + metadata)
ROOT_DIR = os.path.dirname(__file__)
SESSIONS_DIR = os.path.join(ROOT_DIR, "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

# Similarity threshold: cosine distance in L2-normalised space maps to cosine
# similarity. Distance > 1.0 (approx cosine_sim < 0.5) → "not covered".
# We use L2 on normalised vectors: dist = 2*(1 - cos_sim)
# dist > 1.0  →  cos_sim < 0.5  →  weak match
SIMILARITY_DISTANCE_THRESHOLD = 1.0


def build_index(session_id: str, chunks: List[Dict[str, Any]]) -> int:
    """
    Embed all chunks and build a FAISS index for the session.
    Returns the number of chunks indexed.
    """
    model = _get_model()
    texts = [c["text"] for c in chunks]

    print(f"[vector_store] Embedding {len(texts)} chunks...")
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=False,
                              normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype="float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner-product on normalised vecs = cosine sim
    index.add(embeddings)

    _sessions[session_id] = {
        "index": index,
        "metadata": chunks,
    }
    print(f"[vector_store] Session '{session_id}': indexed {index.ntotal} chunks.")

    # Persist index and metadata to disk so sessions survive restarts
    try:
        index_path = os.path.join(SESSIONS_DIR, f"{session_id}.index")
        meta_path = os.path.join(SESSIONS_DIR, f"{session_id}_meta.json")
        faiss.write_index(index, index_path)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False)
        print(f"[vector_store] Session '{session_id}' persisted to disk.")
    except Exception as e:
        print(f"[vector_store] Warning: failed to persist session {session_id}: {e}")

    return index.ntotal


def search(session_id: str, query: str, top_k: int = 5
           ) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Search the session's FAISS index for the top-k most similar chunks.

    Returns:
        (results, below_threshold)
        - results: list of chunk dicts with an added "score" key
        - below_threshold: True if NO result passes the similarity threshold
    """
    # If session not loaded in memory, try to load from disk
    if session_id not in _sessions:
        if not _load_session_from_disk(session_id):
            raise KeyError(f"Session '{session_id}' not found. Please re-upload your PDFs.")

    session = _sessions[session_id]
    model = _get_model()

    query_vec = model.encode([query], normalize_embeddings=True)
    query_vec = np.array(query_vec, dtype="float32")

    k = min(top_k, session["index"].ntotal)
    scores, indices = session["index"].search(query_vec, k)

    results = []
    all_below = True
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        # score here is cosine similarity (IP on normalised vecs), range [-1, 1]
        # Threshold: 0.3 cosine similarity
        chunk = dict(session["metadata"][idx])
        chunk["score"] = float(score)
        results.append(chunk)
        if score >= 0.3:
            all_below = False

    return results, all_below


def session_exists(session_id: str) -> bool:
    if session_id in _sessions:
        return True
    # Check on-disk
    index_path = os.path.join(SESSIONS_DIR, f"{session_id}.index")
    meta_path = os.path.join(SESSIONS_DIR, f"{session_id}_meta.json")
    return os.path.exists(index_path) and os.path.exists(meta_path)


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
    try:
        index_path = os.path.join(SESSIONS_DIR, f"{session_id}.index")
        meta_path = os.path.join(SESSIONS_DIR, f"{session_id}_meta.json")
        if os.path.exists(index_path):
            os.remove(index_path)
        if os.path.exists(meta_path):
            os.remove(meta_path)
    except Exception:
        pass


def _load_session_from_disk(session_id: str) -> bool:
    """Attempt to load a persisted session into memory. Returns True on success."""
    index_path = os.path.join(SESSIONS_DIR, f"{session_id}.index")
    meta_path = os.path.join(SESSIONS_DIR, f"{session_id}_meta.json")
    if not (os.path.exists(index_path) and os.path.exists(meta_path)):
        return False

    try:
        index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        _sessions[session_id] = {
            "index": index,
            "metadata": metadata,
        }
        print(f"[vector_store] Loaded session '{session_id}' from disk ({len(metadata)} chunks).")
        return True
    except Exception as e:
        print(f"[vector_store] Failed to load session {session_id} from disk: {e}")
        return False
