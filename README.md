# PDF Teacher Assistant

Upload multiple PDFs (up to 50 MB total) and chat with an AI that answers like a teacher — strictly from your uploaded documents. No general knowledge, no hallucinations.

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.10+ | `python --version` |
| pip | Latest | `pip --version` |
| Node.js | 18+ | `node --version` |
| npm | Latest | `npm --version` |

---

## Setup

### 1. Get your Gemini API key or OAuth access token
Create a Google Cloud Gemini credential and copy it into the backend `.env`.

### 2. Backend setup

```powershell
cd backend

# Copy the env template and add your key
Copy-Item .env.example .env
notepad .env          # Set GEMINI_API_KEY=YOUR_GEMINI_API_KEY_OR_OAUTH_TOKEN

# Create a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

> **Note**: The first time you run the backend, it will download the `all-MiniLM-L6-v2` model (~90 MB). This is cached and only happens once.

### 3. Start the backend

```powershell
# From /backend with venv active:
uvicorn main:app --reload --port 8000
```

You should see: `Uvicorn running on http://127.0.0.1:8000`

### 4. Frontend setup (new terminal)

```powershell
cd frontend
npm run dev
```

You should see: `Local: http://localhost:5173`

---

## Usage

1. Open `http://localhost:5173` in your browser
2. Click **Select PDF files** or drag & drop PDFs onto the upload zone
3. Click **Process & Start Chat** (wait 10–60s depending on PDF size)
4. Ask questions in plain language — the AI answers from your PDFs only

---

## Project Structure

```
pdf-teacher-assistant/
├── backend/
│   ├── main.py            # FastAPI app (/upload, /chat endpoints)
│   ├── pdf_processor.py   # PyMuPDF text extraction + chunking
│   ├── vector_store.py    # sentence-transformers + FAISS
│   ├── teacher_engine.py  # Claude API + system prompt
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   └── components/
    │       ├── UploadScreen.jsx
    │       ├── FileList.jsx
    │       ├── ChatWindow.jsx
    │       └── MessageBubble.jsx
    ├── index.html
    └── package.json
```

---

## Key Design Decisions

| Aspect | Choice | Reason |
|--------|--------|--------|
| Embeddings | `all-MiniLM-L6-v2` | Free, local, fast, no API needed |
| Vector store | FAISS `IndexFlatIP` | Simple, exact search, in-memory, no server needed |
| Chunking | ~500 words, paragraph-aware | Balances context richness and retrieval precision |
| LLM | Llama 3.5 | Fast, teacher-oriented, PDF-only answers |
| Sessions | In-memory dict | Simple local dev; restart = new session |

---

## Limitations

- Sessions are **in-memory**: restarting the backend clears all sessions
- Only PDFs with **selectable text** are supported (no OCR)
- Maximum **50 MB** combined upload size

---

## Troubleshooting

**"execution of scripts is disabled on this system"**
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

**Model download fails**
Make sure you have internet access on first run. Model is cached in `~/.cache/huggingface/`.

**"Invalid Anthropic API key"**
Check your `.env` file — make sure `ANTHROPIC_API_KEY` is set correctly with no extra spaces.
