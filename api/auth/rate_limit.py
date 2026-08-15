"""Authentication abuse throttles for Bethel public access points."""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

from api.security_alerts import send_security_alert

_LOGIN_WINDOW_SECONDS = 15 * 60
_MAX_IDENTIFIER_FAILURES = 5
_MAX_SOURCE_FAILURES = 20
_REGISTRATION_WINDOW_SECONDS = 60 * 60
_MAX_REGISTRATIONS = 5

_identifier_attempts = defaultdict(deque)
_source_attempts = defaultdict(deque)
_registration_attempts = defaultdict(deque)
_lock = Lock()


def _client_ip(request: Request) -> str:
    """Return the original client address when running behind Cloudflare/Render."""
    cf_ip = (request.headers.get("cf-connecting-ip") or "").strip()
    if cf_ip:
        return cf_ip[:64]
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
    if forwarded:
        return forwarded[:64]
    return (request.client.host if request.client else "unknown")[:64]


def _identifier_key(identifier: str) -> str:
    return identifier.strip().casefold()


def _prune(events, now: float, window: int) -> None:
    while events and now - events[0] >= window:
        events.popleft()


def check_login_allowed(request: Request, identifier: str) -> None:
    """Block credential stuffing by account and by source address."""
    now = monotonic()
    identifier_key = _identifier_key(identifier)
    source_key = _client_ip(request)
    blocked = False
    retry_after = 0
    reason = ""
    with _lock:
        identifier_events = _identifier_attempts[identifier_key]
        source_events = _source_attempts[source_key]
        _prune(identifier_events, now, _LOGIN_WINDOW_SECONDS)
        _prune(source_events, now, _LOGIN_WINDOW_SECONDS)

        identifier_blocked = len(identifier_events) >= _MAX_IDENTIFIER_FAILURES
        source_blocked = len(source_events) >= _MAX_SOURCE_FAILURES
        if identifier_blocked or source_blocked:
            blocked = True
            reason = "account threshold" if identifier_blocked else "source threshold"
            oldest = identifier_events[0] if identifier_blocked else source_events[0]
            retry_after = max(1, int(_LOGIN_WINDOW_SECONDS - (now - oldest)))

    if blocked:
        send_security_alert(
            event="Authentication abuse blocked",
            severity="high",
            summary="Bethel blocked repeated failed login attempts.",
            details=f"Source={source_key}; reason={reason}; retry_after_seconds={retry_after}",
        )
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def record_login_failure(request: Request, identifier: str) -> None:
    now = monotonic()
    with _lock:
        _identifier_attempts[_identifier_key(identifier)].append(now)
        _source_attempts[_client_ip(request)].append(now)


def clear_login_failures(request: Request, identifier: str) -> None:
    with _lock:
        _identifier_attempts.pop(_identifier_key(identifier), None)


def check_registration_allowed(request: Request) -> None:
    """Limit public account creation per source address."""
    address = _client_ip(request)
    now = monotonic()
    blocked = False
    retry_after = 0
    with _lock:
        events = _registration_attempts[address]
        _prune(events, now, _REGISTRATION_WINDOW_SECONDS)
        if len(events) >= _MAX_REGISTRATIONS:
            blocked = True
            retry_after = max(1, int(_REGISTRATION_WINDOW_SECONDS - (now - events[0])))
        else:
            events.append(now)

    if blocked:
        send_security_alert(
            event="Registration abuse blocked",
            severity="medium",
            summary="Bethel blocked excessive public account or reset-related requests.",
            details=f"Source={address}; retry_after_seconds={retry_after}",
        )
        raise HTTPException(
            status_code=429,
            detail="Too many registration attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
