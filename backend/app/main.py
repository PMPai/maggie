from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings
from app.security.rate_limit import RateLimitMiddleware
from app.api.auth import router as auth_router
from app.api.companies import router as companies_router
from app.api.projects import router as projects_router
from app.api.contracts import router as contracts_router
from app.api.documents import router as documents_router
from app.api.payment_applications import router as payment_router
from app.api.approvals import router as approvals_router
from app.api.variations import router as variations_router
from app.api.deductions import router as deductions_router
from app.api.retention_entries import router as retention_entries_router
from app.api.invoices import router as invoices_router
from app.api.collections import router as collections_router
from app.api.financial_adjustments import router as financial_adjustments_router
from app.api.reports import router as reports_router
from app.api.tasks import router as tasks_router
from app.api.dashboard import router as dashboard_router
from app.api.master_budget import router as master_budget_router
from app.api.groups import router as groups_router
from app.api.users import router as users_router

settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """Enforce CSRF token on state-changing requests (POST/PUT/PATCH/DELETE).
    GET/HEAD/OPTIONS are exempt. Token: cookie 'csrf_token' must match header 'X-CSRF-Token'.
    Login endpoint is exempt (no cookie yet at login time)."""
    EXEMPT_PATHS = {"/api/auth/login", "/api/auth/logout", "/api/documents/upload", "/health"}

    async def dispatch(self, request: Request, call_next):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        path = request.url.path
        if any(path == ep or path.startswith(ep + "/") for ep in self.EXEMPT_PATHS):
            return await call_next(request)

        # For multipart/form-data (file upload), skip CSRF to avoid breaking uploads
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("multipart/form-data"):
            return await call_next(request)

        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("X-CSRF-Token")

        # In development, if no CSRF cookie exists yet, allow through (first-time setup)
        if not cookie_token:
            return await call_next(request)

        if not header_token or cookie_token != header_token:
            return JSONResponse(status_code=403, content={"detail": "CSRF token invalid"})

        return await call_next(request)


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
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(RateLimitMiddleware)

    app.include_router(auth_router)
    app.include_router(companies_router)
    app.include_router(projects_router)
    app.include_router(contracts_router)
    app.include_router(documents_router)
    app.include_router(payment_router)
    app.include_router(approvals_router)
    app.include_router(variations_router)
    app.include_router(deductions_router)
    app.include_router(retention_entries_router)
    app.include_router(invoices_router)
    app.include_router(collections_router)
    app.include_router(financial_adjustments_router)
    app.include_router(reports_router)
    app.include_router(tasks_router)
    app.include_router(dashboard_router)
    app.include_router(master_budget_router)
    app.include_router(groups_router)
    app.include_router(users_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "env": settings.APP_ENV}

    return app


app = create_app()
