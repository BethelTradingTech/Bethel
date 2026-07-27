from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
import os
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


PRODUCTION = os.getenv("BETHEL_ENVIRONMENT", "DEVELOPMENT").upper() == "PRODUCTION"
AUTH_PATHS = {
    "/auth/login",
    "/investor/auth/login",
    "/copytrading/auth/login",
    "/copytrading/auth/forgot-password",
    "/copytrading/auth/reset-password",
    "/copytrading/auth/setup-password",
}
LIMIT = int(os.getenv("AUTH_RATE_LIMIT_REQUESTS", "12"))
WINDOW_SECONDS = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "300"))
_attempts: dict[str, deque] = defaultdict(deque)
_lock = Lock()


def client_ip(request) -> str:
    forwarded = request.headers.get("cf-connecting-ip")
    return forwarded or (request.client.host if request.client else "unknown")


def limited(key: str) -> bool:
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=WINDOW_SECONDS)
    with _lock:
        queue = _attempts[key]
        while queue and queue[0] < cutoff:
            queue.popleft()
        if len(queue) >= LIMIT:
            return True
        queue.append(now)
        return False


class ProductionSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if PRODUCTION and path in ("/docs", "/redoc", "/openapi.json"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        if path in AUTH_PATHS and limited(f"{client_ip(request)}:{path}"):
            return JSONResponse(
                {"detail": "Too many authentication requests. Try again later."},
                status_code=429,
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        if request.headers.get("x-forwarded-proto") == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        if (
            path.startswith("/admin/")
            or path.startswith("/auth/")
            or path.startswith("/copytrading/auth/")
        ):
            response.headers["Cache-Control"] = "no-store"
        return response
