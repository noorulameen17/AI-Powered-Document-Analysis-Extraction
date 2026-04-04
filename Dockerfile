FROM python:3.11-slim

WORKDIR /app

# System deps for OCR + PDF parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libglib2.0-0 \
    libnss3 \
    libgdk-pixbuf-xlib-2.0-0 \
    libx11-6 \
    libxrender1 \
    libxext6 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Improve pip robustness for slower networks
ENV PIP_DEFAULT_TIMEOUT=180 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./

# Install Python deps.
# - Use CPU-only torch wheels to dramatically reduce image size.
# - Install spaCy model via direct wheel URL.
RUN pip install --upgrade pip setuptools wheel \
    && pip install --retries 10 --timeout 180 --index-url https://download.pytorch.org/whl/cpu torch==2.7.0 \
    && pip install --retries 10 -r requirements.txt \
    && pip install --retries 10 --timeout 180 https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Use platform-provided PORT when available (Railway)
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
