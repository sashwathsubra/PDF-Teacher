"""
teacher_engine.py
Generates teacher-style answers using Gemini.
Uses ONLY the retrieved PDF chunks — no outside knowledge.
"""

import os
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv
import httpx
import traceback
import logging

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_API_BASE_URL = os.getenv("GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

SYSTEM_PROMPT = (
    "You are a patient, clear teacher. You will be given excerpts retrieved "
    "from the student's uploaded PDF documents and their question. Answer using "
    "ONLY the given excerpts — do not add outside facts, general knowledge, or "
    "any information from sources other than the provided PDF text. If the "
    "excerpts do not fully answer the question, reply exactly with: "
    "\"Incomplete information.\" Do not invent or assume missing details. "
    "If the answer is incomplete, do not include any source citations or page "
    "numbers. Explain the answer simply and clearly, but stay completely faithful to "
    "the excerpts. If you can answer the question, always mention the source file name "
    "and page number at the end of your answer. If the user asks you to summarize a topic, "
    "provide a concise topic summary using only the provided excerpts."
)

NOT_COVERED_RESPONSE = (
    "Incomplete information. The provided PDF excerpts are not sufficient to "
    "answer this fully from your uploaded documents."
)


def _build_gemini_request() -> tuple[str, Dict[str, str]]:
    # Current Gemini/Generative Language API uses the generateContent endpoint
    # Use header-based API key auth via `x-goog-api-key` when available.
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }
    url = f"{GEMINI_API_BASE_URL}/models/{GEMINI_MODEL}:generateContent"
    return url, headers


def build_answer(
    question: str,
    chunks: List[Dict[str, Any]],
    all_below_threshold: bool,
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Given retrieved chunks and the user's question, call Gemini to generate
    a teacher-style answer.

    Returns:
        (answer_text, sources)
        sources: list of {"filename": ..., "page": ...} dicts (deduplicated)
    """
    if all_below_threshold or not chunks:
        return NOT_COVERED_RESPONSE, []

    # Build context string from chunks
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Excerpt {i} — {chunk['filename']}, Page {chunk['page']}]\n"
            f"{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    user_message = (
        f"Here are excerpts from the student's PDFs:\n\n"
        f"{context}\n\n"
        f"---\n\n"
        f"Student's question: {question}"
    )

    try:
        if LLM_PROVIDER != "gemini":
            raise ValueError("Unsupported LLM_PROVIDER. Set LLM_PROVIDER=gemini in .env.")

        if not GEMINI_API_KEY:
            raise ValueError("Missing GEMINI_API_KEY. Set GEMINI_API_KEY in .env.")

        url, headers = _build_gemini_request()
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": SYSTEM_PROMPT + "\n\n" + user_message}],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            },
        }

        # Structured logging (do NOT log API keys)
        logger = logging.getLogger(__name__)
        if not logging.getLogger().handlers:
            logging.basicConfig(level=logging.INFO)
        logger.info("[llm] request url=%s model=%s", url, GEMINI_MODEL)
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as http_exc:
                status = http_exc.response.status_code
                body_snippet = http_exc.response.text[:1000]
                if status in (401, 403):
                    return (
                        "⚠️ Invalid Gemini API key or unauthorized request. "
                        "Please check GEMINI_API_KEY in .env and verify the key in AI Studio.",
                        [],
                    )
                if status == 429:
                    return (
                        "⚠️ Request quota exceeded for Gemini. Check billing, quota, or try a different key.",
                        [],
                    )
                return (f"⚠️ LLM API error ({status}): {body_snippet}", [])

            try:
                data = response.json()
            except Exception:
                logger.exception("Failed to parse LLM response as JSON")
                return ("⚠️ Failed to parse LLM response as JSON.", [])

        # Parse answer safely
        try:
            answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            # Return the raw response on parse errors (trimmed)
            snippet = str(data)[:1000]
            return (f"⚠️ Unexpected LLM response format: {snippet}", [])

        # Post-process answer:
        # - Convert markdown-style bold/italic markers to HTML <strong> for bold
        #   (user requested that asterisks be removed and text remain bold).
        # - Remove any trailing LLM-provided `Source:` lines and append a
        #   canonical `Source file: {filename}, Page {page}` line using the
        #   first source from `chunks` so the format is consistent.
        import re

        # Convert **bold** and *italic* -> <strong>text</strong> (prefer bold)
        def _convert_asterisk_to_strong(text: str) -> str:
            # Replace double-asterisk bold first
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            # Replace single-asterisk emphasis by strong as well
            text = re.sub(r"\*(.+?)\*", r"<strong>\1</strong>", text)
            return text

        answer = _convert_asterisk_to_strong(answer)

        # Remove any LLM-inserted source/footer lines that start with 'Source:'
        # Remove such lines anywhere in the text (case-insensitive, line-based)
        answer = re.sub(r"(?im)^\s*Source:.*(?:\r?\n)?", "", answer).strip()

        normalized = re.sub(r"\s+", " ", answer).strip()
        if re.match(r"(?i)^Incomplete (information|info)\b", normalized):
            return NOT_COVERED_RESPONSE, []

        # Append canonical source line using the first chunk (if present)
        if chunks:
            first = chunks[0]
            src_line = f"\n\nSource file: {first.get('filename','unknown')}, Page {first.get('page', -1)}"
            answer = answer + src_line
    except httpx.HTTPStatusError as exc:
        logger = logging.getLogger(__name__)
        status = exc.response.status_code
        body = exc.response.text
        logger.error("LLM HTTP error %s: %s", status, body)
        if status in (401, 403):
            answer = (
                "⚠️ Invalid Gemini API key or unauthorized request. "
                "Please check GEMINI_API_KEY in .env and restart the server."
            )
        else:
            answer = f"⚠️ LLM API error ({status}): {body}"
    except ValueError as exc:
        logger = logging.getLogger(__name__)
        logger.error("Configuration error: %s", exc)
        answer = f"⚠️ Configuration error: {str(exc)}"
    except Exception:
        logger = logging.getLogger(__name__)
        logger.exception("Unexpected error in build_answer")
        raise

    # Collect unique sources
    seen = set()
    sources = []
    for chunk in chunks:
        key = (chunk["filename"], chunk["page"])
        if key not in seen:
            seen.add(key)
            sources.append({"filename": chunk["filename"], "page": chunk["page"]})

    return answer, sources
