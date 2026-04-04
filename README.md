# AI-Powered Document Analysis & Extraction

## What this is

A full-stack app that accepts a **PDF / DOCX / image** document as **Base64**, extracts text (OCR for images), then returns:

- **AI summary** (transformer-based, with invoice-aware formatting)
- **Key entities** (names, organizations, dates) + **financial amounts**
- **Sentiment** (transformer-based; invoices default to Neutral)

Backend: **FastAPI + Celery + Redis**. Frontend: **Next.js + Tailwind + shadcn/ui**.

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

## Configuration

Create a local `.env` from `.env.example`.

Important vars:

- `API_KEY` (required)
- `REDIS_URL` (required for Celery)
- `CORS_ORIGINS` (comma-separated)
- `NEXT_PUBLIC_API_BASE_URL` (frontend → backend URL)

---

## Run locally (no Docker)

### Backend

1. Copy env:
   - Create `.env` from `.env.example` and set `API_KEY`.
2. Install deps:
   - `pip install -r requirements.txt`
3. Start Redis (locally, or via Docker).
4. Run API:
   - `uvicorn src.main:app --host 0.0.0.0 --port 8000`
5. Run worker (separate terminal):
   - `celery -A src.tasks.celery_app.celery_app worker --loglevel=INFO`

### Frontend

1. In `frontend/`, create `.env.local` (or set env in your shell):
   - `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
2. Install deps and run dev server.

---

## Run with Docker (recommended)

This brings up `redis`, `api`, and `worker`:

- Ensure `.env` exists in repo root.
- Start with `docker-compose.yml`.

---

## Deployment (one practical path)

### Backend

Deploy the **FastAPI API + Celery worker + Redis** together (same VPC/network) using any container host:

- Render / Railway / Fly.io / Azure Container Apps / EC2
- Use one Redis instance (managed or container)
- Run **two processes** from the same image:
  - API: `uvicorn src.main:app --host 0.0.0.0 --port 8000`
  - Worker: `celery -A src.tasks.celery_app.celery_app worker --loglevel=INFO`

Set environment variables on the platform:

- `API_KEY` (secret)
- `REDIS_URL`
- `CORS_ORIGINS` (include your frontend domain)

### Frontend

Deploy `frontend/` on Vercel (or similar) and configure:

- `NEXT_PUBLIC_API_BASE_URL=https://<your-backend-domain>`

---

## Notes

- First run may be slower because transformer models download/load.
- For best OCR results, upload clear images (high contrast).
