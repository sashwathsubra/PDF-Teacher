"""
vector_store.py
Manages embeddings and FAISS index per session.
Uses Google's Gemini Embedding API (free tier, no local model, no torch)
instead of sentence-transformers — this keeps memory usage low enough
to run on Render's free 512MB instance.
"""

from __future__ import annotations

import numpy as np
import faiss
import httpx
import os
import json
import time
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Gemini embedding config
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_API_BASE_URL = os.getenv(
    "GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
).rstrip("/")
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001").strip()

_BATCH_SIZE = 50  # texts per API call
_MAX_RETRIES = 3


def preload_models() -> None:
    """
    No local model to preload anymore — kept as a no-op so existing
    build commands (`python preload_models.py`) don't break.
    """
    if not GEMINI_API_KEY:
        print("[vector_store] WARNING: GEMINI_API_KEY not set.")
    else:
        print("[vector_store] Using Gemini Embedding API — no local model to preload.")


def _embed_batch(texts: List[str], task_type: str) -> np.ndarray:
    """
    Call Gemini's batchEmbedContents endpoint for a batch of texts.
    task_type: "RETRIEVAL_DOCUMENT" for chunks being indexed,
               "RETRIEVAL_QUERY" for the user's question.
    """
    if not GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_API_KEY. Set it in your environment.")

    url = f"{GEMINI_API_BASE_URL}/models/{EMBEDDING_MODEL}:batchEmbedContents"
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "requests": [
            {
                "model": f"models/{EMBEDDING_MODEL}",
                "content": {"parts": [{"text": t}]},
                "taskType": task_type,
            }
            for t in texts
        ]
    }

    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code == 429:
                    wait = 2 ** attempt
                    print(f"[vector_store] Rate limited, retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                data = response.json()
                vectors = [e["values"] for e in data["embeddings"]]
                return np.array(vectors, dtype="float32")
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code in (401, 403):
                raise ValueError(
                    "Invalid Gemini API key or unauthorized request for embeddings."
                ) from exc
            time.sleep(1)
        except Exception as exc:
            last_exc = exc
            time.sleep(1)

    raise RuntimeError(f"Failed to get embeddings after {_MAX_RETRIES} attempts: {last_exc}")


def _embed_texts(texts: List[str], task_type: str) -> np.ndarray:
    """Embed a list of texts in batches, L2-normalise, and concatenate."""
    all_vecs = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        vecs = _embed_batch(batch, task_type)
        all_vecs.append(vecs)
    embeddings = np.vstack(all_vecs)

    # L2-normalise so inner product == cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1e-8
    embeddings = embeddings / norms
    return embeddings.astype("float32")


# ---------------------------------------------------------------------------
# In-memory session store
# { session_id: { "index": faiss.Index, "metadata": [chunk_dict, ...] } }
# ---------------------------------------------------------------------------
_sessions: Dict[str, Dict[str, Any]] = {}

ROOT_DIR = os.path.dirname(__file__)
SESSIONS_DIR = os.path.join(ROOT_DIR, "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

SIMILARITY_DISTANCE_THRESHOLD = 1.0


def build_index(session_id: str, chunks: List[Dict[str, Any]]) -> int:
    """
    Embed all chunks via Gemini and build a FAISS index for the session.
    Returns the number of chunks indexed.
    """
    texts = [c["text"] for c in chunks]

    print(f"[vector_store] Embedding {len(texts)} chunks via Gemini...")
    embeddings = _embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    _sessions[session_id] = {
        "index": index,
        "metadata": chunks,
    }
    print(f"[vector_store] Session '{session_id}': indexed {index.ntotal} chunks.")

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
    """
    if session_id not in _sessions:
        if not _load_session_from_disk(session_id):
            raise KeyError(f"Session '{session_id}' not found. Please re-upload your PDFs.")

    session = _sessions[session_id]

    query_vec = _embed_texts([query], task_type="RETRIEVAL_QUERY")

    k = min(top_k, session["index"].ntotal)
    scores, indices = session["index"].search(query_vec, k)

    results = []
    all_below = True
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        chunk = dict(session["metadata"][idx])
        chunk["score"] = float(score)
        results.append(chunk)
        if score >= 0.3:
            all_below = False

    return results, all_below


def session_exists(session_id: str) -> bool:
    if session_id in _sessions:
        return True
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