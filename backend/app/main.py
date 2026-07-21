from fastapi import FastAPI
from app.config import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Engineering Contract & Billing System",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "env": settings.APP_ENV}

    return app


app = create_app()
