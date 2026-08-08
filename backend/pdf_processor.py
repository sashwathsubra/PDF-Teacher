"""
pdf_processor.py
Extracts text from PDFs using PyMuPDF and splits into tagged chunks.
No OCR — text-layer only.
"""

import fitz  # PyMuPDF
import re
from typing import List, Dict, Any


CHUNK_SIZE_WORDS = 500
CHUNK_OVERLAP_WORDS = 50


def extract_chunks_from_pdf(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Extract text from a PDF and split into overlapping chunks.

    Returns a list of chunk dicts:
        {
            "text": str,
            "filename": str,
            "page": int,
            "chunk_index": int,
        }

    If the PDF has no extractable text, returns a single sentinel dict with
    the key "skipped" = True.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        return [{"skipped": True, "filename": filename, "reason": str(e)}]

    # Gather all text per page
    pages_text: List[tuple[int, str]] = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text and text.strip():
            pages_text.append((page_num + 1, text.strip()))

    doc.close()

    if not pages_text:
        return [{"skipped": True, "filename": filename,
                 "reason": "no readable text"}]

    # Build chunks across pages, keeping page-number tags
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    # We chunk per page to keep source attribution tight.
    # A page's text is further split if it is very long.
    for page_num, page_text in pages_text:
        page_chunks = _split_text_into_chunks(page_text)
        for chunk_text in page_chunks:
            if chunk_text.strip():
                chunks.append({
                    "text": chunk_text.strip(),
                    "filename": filename,
                    "page": page_num,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1

    if not chunks:
        return [{"skipped": True, "filename": filename,
                 "reason": "no readable text after chunking"}]

    return chunks


def _split_text_into_chunks(text: str) -> List[str]:
    """
    Split a block of text into ~CHUNK_SIZE_WORDS word chunks with
    CHUNK_OVERLAP_WORDS word overlap. Tries to split on paragraph
    boundaries first.
    """
    # Normalise whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Split into paragraphs
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]

    chunks: List[str] = []
    current_words: List[str] = []

    for para in paragraphs:
        para_words = para.split()
        current_words.extend(para_words)

        if len(current_words) >= CHUNK_SIZE_WORDS:
            chunk_text = " ".join(current_words[:CHUNK_SIZE_WORDS])
            chunks.append(chunk_text)
            # Keep overlap
            current_words = current_words[CHUNK_SIZE_WORDS - CHUNK_OVERLAP_WORDS:]

    # Flush remainder
    if current_words:
        chunks.append(" ".join(current_words))

    # If the text produced no paragraphs (e.g. one huge line), fall back
    if not chunks and text.strip():
        words = text.split()
        for i in range(0, len(words), CHUNK_SIZE_WORDS - CHUNK_OVERLAP_WORDS):
            chunk_words = words[i: i + CHUNK_SIZE_WORDS]
            if chunk_words:
                chunks.append(" ".join(chunk_words))

    return chunks
