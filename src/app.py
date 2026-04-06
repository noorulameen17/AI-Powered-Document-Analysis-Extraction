from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api.routes import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="AI Document Analysis API", version="1.0.0")

    # Always allow the submitted Vercel frontend (so the deployed demo works even
    # if the hosting provider doesn't inject CORS_ORIGINS correctly).
    default_origins = {
        "https://ai-powered-document-analysis-extrac-psi.vercel.app",
    }

    env_origins = [o.strip() for o in (settings.CORS_ORIGINS or "").split(",") if o.strip()]
    origins = sorted(default_origins.union(env_origins))

    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_router, prefix="/api")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
