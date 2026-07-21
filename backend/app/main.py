from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings
from app.api.auth import router as auth_router
from app.api.companies import router as companies_router
from app.api.projects import router as projects_router
from app.api.contracts import router as contracts_router
from app.api.documents import router as documents_router

settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="Engineering Contract & Billing System",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(auth_router)
    app.include_router(companies_router)
    app.include_router(projects_router)
    app.include_router(contracts_router)
    app.include_router(documents_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "env": settings.APP_ENV}

    return app


app = create_app()
