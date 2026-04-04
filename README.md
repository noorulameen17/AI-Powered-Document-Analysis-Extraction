# AI-Powered Document Analysis & Extraction

## What this is

A full-stack app that accepts a **PDF / DOCX / image** document as **Base64**, extracts text (OCR for images), then returns:

- **AI summary** (transformer-based, with invoice-aware formatting)
- **Key entities** (names, organizations, dates) + **financial amounts**
- **Sentiment** (transformer-based; invoices default to Neutral)

Backend: **FastAPI + Celery + Redis**. Frontend: **Next.js + Tailwind + shadcn/ui**.

---

## Architecture overview

**High-level components**

- **Next.js frontend**: upload UI → converts file to Base64 → calls backend API.
- **FastAPI backend**: validates API key, receives request, queues a Celery task, and returns the computed result.
- **Celery worker**: does the CPU-heavy work (text extraction + AI analysis).
- **Redis**: message broker + result backend for Celery.

**Request flow**

1. User uploads a document in the browser.
2. Frontend converts the file to Base64 and sends `POST /api/document-analyze` with `x-api-key`.
3. Backend enqueues a Celery job in Redis.
4. Worker processes the job:
   - Extracts text (PDF/DOCX/OCR)
   - Runs AI summarization + sentiment
   - Extracts entities + amounts
5. Worker returns the output via Redis and the API responds with a JSON payload.

---

## Repository structure (submission layout)

```
README.md
src/
  main.py
requirements.txt
.env.example
```

> Note: The legacy `backend/` folder has been removed. All backend source code is under `src/`.

---

## Tech stack (complete)

### Backend

- **Python 3.11+**
- **FastAPI** (REST API)
- **Uvicorn** (ASGI server)
- **Celery** (async task queue)
- **Redis** (Celery broker + result backend)
- **Text extraction**
  - `pdfplumber` (PDF)
  - `python-docx` (DOCX)
  - `pytesseract` + `Pillow` (OCR for images)
- **NLP / AI (local models)**
  - `transformers` (summarization + sentiment)
  - `torch` (model runtime)
  - `spaCy` (`en_core_web_sm`) for NER
- **Config**
  - `python-dotenv` for `.env`

### Frontend

- **Next.js (React)**
- **TypeScript**
- **Tailwind CSS**
- **shadcn/ui** components
- **lucide-react** icons

### Container / Infra

- `docker-compose` (services: `redis`, `api`, `worker`)
- `Dockerfile` (includes OCR dependencies and Python deps)

---

## AI tools used

### Runtime AI (in the application)

This project uses **local (on-device) Hugging Face transformer models** via the `transformers` library:

- **Summarization**: `sshleifer/distilbart-cnn-12-6` (with chunking + fallback)
- **Sentiment**: `distilbert-base-uncased-finetuned-sst-2-english`

NER / entities are extracted with:

- **spaCy**: `en_core_web_sm`

> Note: Invoice-like documents are detected heuristically and summarized using a structured template to produce more useful “invoice-style” summaries.

### AI-assisted development

During development, **GitHub Copilot** was used to speed up implementation, refactoring, and documentation (e.g., generating boilerplate and suggesting improvements). The deployed app itself runs locally using the models listed above.

---

## How it works (pipeline)

1. **Upload (browser):** user selects a file → frontend converts it to **Base64**.
2. **API request:** frontend calls `POST /api/document-analyze` with header `x-api-key`.
3. **Celery task:** the API enqueues the job in Redis and **waits for the result** (simple hackathon-friendly flow).
4. **Extraction:** backend extracts text based on file type:
   - PDF → `pdfplumber`
   - DOCX → `python-docx`
   - Image → OCR via `pytesseract`
5. **AI analysis:**
   - **Summarization:** transformer summarization with chunking; invoice-aware formatting when detected.
   - **Entities:** spaCy NER + custom amount regex.
   - **Sentiment:** transformer classifier (invoices forced to Neutral).

---

## API

### Authentication (Option A — API key)

This project uses **Option A: API key header authentication**.

- Every request must include:
  - Header: `x-api-key: <YOUR_API_KEY>`
- The backend compares this to `API_KEY` in your `.env`.
- Missing/invalid key returns **401 Unauthorized**.

**Example API key (placeholder):**

- `sk_demo_1234567890`

Put it in your `.env`:

- `API_KEY=sk_demo_1234567890`

And send it as a header:

- `x-api-key: sk_demo_1234567890`

### Endpoint

- `POST /api/document-analyze`

Request body:

```json
{
  "fileName": "sample.pdf",
  "fileType": "pdf",
  "fileBase64": "..."
}
```

Response (success):

```json
{
  "status": "success",
  "fileName": "sample.pdf",
  "summary": "...",
  "entities": {
    "names": [],
    "dates": [],
    "organizations": [],
    "amounts": []
  },
  "sentiment": "Neutral"
}
```

---

## Setup instructions

### 1) Configure environment

Create a local `.env` from `.env.example`.

Important vars:

- `API_KEY` (required)
- `REDIS_URL` (required for Celery)
- `CORS_ORIGINS` (comma-separated)
- `NEXT_PUBLIC_API_BASE_URL` (frontend → backend URL)

### 2) Run locally (no Docker)

Backend:

1. Install deps: `pip install -r requirements.txt`
2. Start Redis (locally, or via Docker)
3. Run API: `uvicorn src.main:app --host 0.0.0.0 --port 8000`
4. Run worker (separate terminal): `celery -A src.tasks.celery_app.celery_app worker --loglevel=INFO`

Frontend:

1. In `frontend/`, create `.env.local`:
   - `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
2. Install deps and run dev server.

### 3) Run with Docker (recommended)

- Ensure `.env` exists in repo root.
- Start `redis`, `api`, and `worker` using `docker-compose.yml`.

---

## Known limitations

- **Cold start**: first request can be slow while transformer models download/load.
- **OCR quality** depends heavily on image clarity; low-resolution scans may reduce accuracy.
- **NER limitations**: `en_core_web_sm` is lightweight and may miss some entities.
- **Amount extraction** is regex-based; some formats may be missed or misinterpreted.
- **Large documents** may hit timeouts (the API waits for the Celery result).
- **Deployment**: for production-grade deployments you’d typically return a job id instead of blocking.

---

## Notes

- For best OCR results, upload clear images (high contrast).
