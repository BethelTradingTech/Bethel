"""Small fail-closed login throttle for the single-process Bethel API."""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request


_WINDOW_SECONDS = 15 * 60
_MAX_FAILURES = 5
_attempts = defaultdict(deque)
_registration_attempts = defaultdict(deque)
_lock = Lock()
_REGISTRATION_WINDOW_SECONDS = 60 * 60
_MAX_REGISTRATIONS = 5


def _key(request: Request, identifier: str) -> tuple[str, str]:
    address = request.client.host if request.client else "unknown"
    return address, identifier.strip().casefold()


def check_login_allowed(request: Request, identifier: str) -> None:
    key = _key(request, identifier)
    now = monotonic()
    with _lock:
        events = _attempts[key]
        while events and now - events[0] > _WINDOW_SECONDS:
            events.popleft()
        if len(events) >= _MAX_FAILURES:
            raise HTTPException(
                status_code=429,
                detail="Too many failed login attempts. Try again later.",
                headers={"Retry-After": str(_WINDOW_SECONDS)},
            )


def record_login_failure(request: Request, identifier: str) -> None:
    with _lock:
        _attempts[_key(request, identifier)].append(monotonic())


def clear_login_failures(request: Request, identifier: str) -> None:
    with _lock:
        _attempts.pop(_key(request, identifier), None)


def check_registration_allowed(request: Request) -> None:
    """Limit public account creation per source address."""
    address = request.client.host if request.client else "unknown"
    now = monotonic()
    with _lock:
        events = _registration_attempts[address]
        while events and now - events[0] > _REGISTRATION_WINDOW_SECONDS:
            events.popleft()
        if len(events) >= _MAX_REGISTRATIONS:
            raise HTTPException(
                status_code=429,
                detail="Too many registration attempts. Try again later.",
                headers={"Retry-After": str(_REGISTRATION_WINDOW_SECONDS)},
            )
        events.append(now)
