"""Rate limiting middleware — in-memory sliding window for development.
Production should use Redis-based rate limiting (e.g. slowapi)."""
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter.
    Limits: 5 failed logins/min per IP, 100 API requests/min per IP."""

    def __init__(self, app, login_limit=5, api_limit=100, window_seconds=60):
        super().__init__(app)
        self.login_limit = login_limit
        self.api_limit = api_limit
        self.window = window_seconds
        self._login_attempts: dict[str, list[float]] = defaultdict(list)
        self._api_requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Login rate limiting
        if request.url.path == "/api/auth/login" and request.method == "POST":
            attempts = self._login_attempts[client_ip]
            self._login_attempts[client_ip] = [t for t in attempts if now - t < self.window]
            if len(self._login_attempts[client_ip]) >= self.login_limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many login attempts. Try again later."}
                )
            response = await call_next(request)
            if response.status_code == 401:
                self._login_attempts[client_ip].append(now)
            return response

        # General API rate limiting
        if request.url.path.startswith("/api/"):
            reqs = self._api_requests[client_ip]
            self._api_requests[client_ip] = [t for t in reqs if now - t < self.window]
            if len(self._api_requests[client_ip]) >= self.api_limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."}
                )
            self._api_requests[client_ip].append(now)

        return await call_next(request)
