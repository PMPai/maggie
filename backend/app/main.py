from fastapi import FastAPI
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
from app.api.standard_items import router as standard_items_router
from app.api.variations import router as variations_router
from app.api.deductions import router as deductions_router
from app.api.retention_entries import router as retention_entries_router
from app.api.invoices import router as invoices_router
from app.api.collections import router as collections_router
from app.api.financial_adjustments import router as financial_adjustments_router
from app.api.item_mappings import router as item_mappings_router
from app.api.matching_reviews import router as matching_reviews_router
from app.api.reports import router as reports_router
from app.api.tasks import router as tasks_router
from app.api.dashboard import router as dashboard_router

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
    app.add_middleware(RateLimitMiddleware)

    app.include_router(auth_router)
    app.include_router(companies_router)
    app.include_router(projects_router)
    app.include_router(contracts_router)
    app.include_router(documents_router)
    app.include_router(payment_router)
    app.include_router(approvals_router)
    app.include_router(standard_items_router)
    app.include_router(variations_router)
    app.include_router(deductions_router)
    app.include_router(retention_entries_router)
    app.include_router(invoices_router)
    app.include_router(collections_router)
    app.include_router(financial_adjustments_router)
    app.include_router(item_mappings_router)
    app.include_router(matching_reviews_router)
    app.include_router(reports_router)
    app.include_router(tasks_router)
    app.include_router(dashboard_router)

    @app.get("/health")
    async def health():
        return {"status": "ok", "env": settings.APP_ENV}

    return app


app = create_app()
