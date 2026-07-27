from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware

from api.database import SessionLocal
from api.operations.models import SecurityEvent


SENSITIVE_PREFIXES = (
    "/auth/",
    "/copytrading/auth/",
    "/admin/",
    "/kyc/",
    "/payments/",
    "/broker-accounts/",
    "/legal/",
    "/profit-share/",
    "/subscriptions/",
)


def severity(status_code: int) -> str:
    if status_code >= 500:
        return "CRITICAL"
    if status_code in (401, 403, 429):
        return "WARNING"
    return "INFO"


def event_type(path: str, status_code: int) -> str:
    if "login" in path:
        return "LOGIN_SUCCESS" if status_code < 400 else "LOGIN_FAILURE"
    if "forgot-password" in path:
        return "PASSWORD_RESET_REQUEST"
    if "reset-password" in path or "setup-password" in path:
        return "PASSWORD_CHANGE"
    if path.startswith("/admin/"):
        return "ADMIN_REQUEST"
    if status_code >= 500:
        return "SERVER_ERROR"
    if status_code in (401, 403):
        return "ACCESS_DENIED"
    return "SECURITY_SENSITIVE_REQUEST"


class SecurityAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = datetime.utcnow()
        response = None
        status_code = 500
        detail = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as error:
            detail = f"{type(error).__name__}: {error}"[:2000]
            raise
        finally:
            path = request.url.path
            should_log = (
                path.startswith(SENSITIVE_PREFIXES)
                or status_code in (401, 403, 429)
                or status_code >= 500
            )
            if should_log:
                db = SessionLocal()
                try:
                    elapsed = int((datetime.utcnow() - started).total_seconds() * 1000)
                    db.add(SecurityEvent(
                        event_type=event_type(path, status_code),
                        severity=severity(status_code),
                        method=request.method,
                        path=path[:500],
                        status_code=status_code,
                        actor=None,
                        ip_address=request.client.host if request.client else None,
                        user_agent=request.headers.get("user-agent", "")[:500],
                        detail=detail or f"duration_ms={elapsed}",
                    ))
                    db.commit()
                except Exception:
                    db.rollback()
                finally:
                    db.close()
