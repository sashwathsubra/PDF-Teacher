"""
main.py
FastAPI application — PDF Teacher Assistant backend.

Endpoints:
  POST /upload  — upload PDFs, extract, embed, store in FAISS, return session_id
  POST /chat    — ask a question, retrieve + LLM answer, return answer + sources
"""

import asyncio
import logging
import os
import re
import uuid
from typing import List

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from dotenv import load_dotenv
from pdf_processor import extract_chunks_from_pdf
from vector_store import build_index, preload_models, search, session_exists
from teacher_engine import build_answer

load_dotenv()

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pdf-teacher")

app = FastAPI(title="PDF Teacher Assistant", version="1.0.0")

allowed = os.getenv("ALLOWED_ORIGINS")
if allowed:
    origins = [o.strip() for o in allowed.split(",") if o.strip()]
else:
    origins = ["*"]  # dev fallback

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Preload heavy models on startup only if explicitly enabled. On low-memory
# Render free instances this can cause "out of memory" during startup.
if os.getenv("PRELOAD_AT_STARTUP", "false").strip().lower() in {"1", "true", "yes"}:
    @app.on_event("startup")
    async def on_startup():
        try:
            preload_models()
        except Exception as e:
            logger.warning("[startup] Failed to preload models: %s", e)


def _sanitize_filename(name: str) -> str:
    name = os.path.basename(name or "unknown.pdf")
    # Replace suspicious chars with underscore, keep common safe chars
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name[:200]

MAX_TOTAL_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    session_id: str
    question: str


class SourceItem(BaseModel):
    filename: str
    page: int


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem]


class UploadResponse(BaseModel):
    session_id: str
    total_chunks: int
    skipped_files: List[str]
    processed_files: List[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/upload", response_model=UploadResponse)
async def upload_pdfs(files: List[UploadFile] = File(...)):
    """
    Accept multiple PDF files, extract text, embed, store in FAISS.
    Returns a session_id to use for subsequent /chat calls.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    # Read all files into memory and validate total size
    file_data: List[tuple[str, bytes]] = []
    total_size = 0
    for f in files:
        content = await f.read()
        total_size += len(content)
        if total_size > MAX_TOTAL_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Combined file size exceeds 50 MB limit. "
                    f"Current total: {total_size / (1024*1024):.1f} MB. "
                    "Please remove some files and try again."
                ),
            )
        # Basic PDF validation: check PDF magic bytes
        stripped = content.lstrip()
        if not stripped.startswith(b"%PDF"):
            # Skip non-PDF/binary files; record as skipped later
            file_data.append((f.filename or "unknown.pdf", None))
            continue

        filename = _sanitize_filename(f.filename or "unknown.pdf")
        file_data.append((filename, content))

    # Process PDFs in a thread (CPU-bound)
    all_chunks = []
    skipped_files = []
    processed_files = []

    loop = asyncio.get_event_loop()

    for filename, content in file_data:
        if content is None:
            skipped_files.append(filename)
            continue

        try:
            chunks = await loop.run_in_executor(
                None, extract_chunks_from_pdf, content, filename
            )
        except Exception as e:
            logger.warning("Failed to extract %s: %s", filename, e)
            skipped_files.append(filename)
            continue
        # Check if the first (and only) chunk is a skip sentinel
        if chunks and chunks[0].get("skipped"):
            skipped_files.append(filename)
        else:
            valid_chunks = [c for c in chunks if not c.get("skipped")]
            if valid_chunks:
                all_chunks.extend(valid_chunks)
                processed_files.append(filename)
            else:
                skipped_files.append(filename)

    if not all_chunks:
        raise HTTPException(
            status_code=422,
            detail=(
                "None of the uploaded files contained readable text. "
                "Please upload PDFs with selectable text."
            ),
        )

    # Build FAISS index
    session_id = str(uuid.uuid4())
    total_chunks = await loop.run_in_executor(
        None, build_index, session_id, all_chunks
    )

    return UploadResponse(
        session_id=session_id,
        total_chunks=total_chunks,
        skipped_files=skipped_files,
        processed_files=processed_files,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Accept a question for a given session, retrieve top-5 chunks, 
    generate a teacher-style answer via Claude.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not session_exists(req.session_id):
        raise HTTPException(
            status_code=404,
            detail=(
                "Session not found. Your PDF session may have expired. "
                "Please re-upload your PDFs."
            ),
        )

    loop = asyncio.get_event_loop()

    try:
        # Retrieve
        chunks, all_below = await loop.run_in_executor(
            None, search, req.session_id, req.question, 5
        )

        # Generate answer
        answer, sources = await loop.run_in_executor(
            None, build_answer, req.question, chunks, all_below
        )

        # If the LLM returned a user-facing error message (prefixed with the
        # warning emoji), surface it as a 503 so the frontend can handle it.
        if isinstance(answer, str) and answer.startswith("⚠️"):
            raise HTTPException(status_code=503, detail=answer)

        return ChatResponse(
            answer=answer,
            sources=[SourceItem(**s) for s in sources],
        )
    except HTTPException:
        # Re-raise expected HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors server-side but return a generic message to clients
        logger.exception("Unexpected error in /chat")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    # Add security headers (sensible defaults for API)
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    # Minimal CSP to prevent inline script/style execution if ever serving HTML
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response
