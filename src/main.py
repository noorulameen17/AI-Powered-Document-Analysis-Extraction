"""Entry point for the FastAPI backend.

Hackathon-required layout:

your-repo/
  src/
    main.py

Run (example):
- uvicorn src.main:app --host 0.0.0.0 --port 8000
"""

from .app import create_app

app = create_app()

__all__ = ["app"]
