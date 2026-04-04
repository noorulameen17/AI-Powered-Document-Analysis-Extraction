from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api.routes import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="AI Document Analysis API", version="1.0.0")

    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"] ,
            allow_headers=["*"],
        )

    app.include_router(api_router, prefix="/api")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
