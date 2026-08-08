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

> Deployment note: to avoid slow first requests in server environments that don't persist caches
> between restarts, preload the embedding model during the build step. For example, when deploying
> to Render add the following build command after `pip install`:
>
> ```bash
> python -m backend.scripts.preload_models
> ```
>
> Alternatively run the helper directly in your Dockerfile or CI to cache the HuggingFace model
> into the image filesystem so the running container doesn't download it on first request.

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

**Deploying**

- Frontend (Vercel):
    - Root directory: `frontend`
    - Framework: Vite
    - Add environment variable `VITE_API_URL` → `https://<your-backend-url>`

- Backend (Render recommended):
    - Root directory: `backend`
    - Build command: `pip install -r requirements.txt && python -m scripts.preload_models`
    - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
    - Set environment variables in Render dashboard: `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, and `ALLOWED_ORIGINS` (comma-separated allowed origins)
    - Pin Python by including `runtime.txt` in `backend/` (already added)

Note: persistent local files (the `backend/sessions/` folder) may be cleared on container restarts or redeploys on free tiers. Consider using an external persistent store (S3, GCS, or a managed DB) for production session persistence.

---

**Security & secret handling**

- Never commit real API keys or secrets to the repository. Ensure `backend/.env` is included in `.gitignore` (it is). If you accidentally pushed secrets, rotate those credentials immediately.
- To remove a secret from Git history, use one of these approaches (choose one):
    - BFG Repo-Cleaner (recommended for simplicity):
        ```bash
        # Install BFG, then:
        bfg --delete-files backend/.env
        git reflog expire --expire=now --all
        git gc --prune=now --aggressive
        git push --force
        ```
    - git filter-repo (more powerful):
        ```bash
        pip install git-filter-repo
        git filter-repo --path backend/.env --invert-paths
        git push --force
        ```

- After rewriting history, rotate any exposed credentials (create a new Gemini key).

**Production security checklist**

- Set `ALLOWED_ORIGINS` to your frontend origin (e.g. `https://pdf-teacher.vercel.app`) in the backend deployment environment — do not leave `*` in production.
- Set environment variables in your host (Render, Railway, Fly): `GEMINI_API_KEY`, `GEMINI_MODEL`, `LLM_PROVIDER`, and `ALLOWED_ORIGINS`.
- Use HTTPS and enable HSTS at the proxy/load-balancer level (the app sets `Strict-Transport-Security` header but TLS is required at the edge).
- Consider an external, persistent vector store and metadata store (S3 + managed DB) for production instead of local `backend/sessions/`.
- Add rate-limiting / abuse protection (IP-based throttling) before public launch.

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
