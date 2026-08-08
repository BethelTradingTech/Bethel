"""Authentication abuse throttles for Bethel public access points."""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

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
    """Block credential stuffing by account and by source address.

    Identifier throttling remains effective if an attacker rotates IP addresses,
    while source throttling limits one address from spraying many accounts.
    """
    now = monotonic()
    identifier_key = _identifier_key(identifier)
    source_key = _client_ip(request)
    with _lock:
        identifier_events = _identifier_attempts[identifier_key]
        source_events = _source_attempts[source_key]
        _prune(identifier_events, now, _LOGIN_WINDOW_SECONDS)
        _prune(source_events, now, _LOGIN_WINDOW_SECONDS)

        if len(identifier_events) >= _MAX_IDENTIFIER_FAILURES or len(source_events) >= _MAX_SOURCE_FAILURES:
            oldest = identifier_events[0] if len(identifier_events) >= _MAX_IDENTIFIER_FAILURES else source_events[0]
            retry_after = max(1, int(_LOGIN_WINDOW_SECONDS - (now - oldest)))
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
    # A successful login clears the account-specific failures. Source failures
    # remain briefly so one successful credential cannot reset a password-spray
    # attack against other accounts from the same address.
    with _lock:
        _identifier_attempts.pop(_identifier_key(identifier), None)


def check_registration_allowed(request: Request) -> None:
    """Limit public account creation per source address."""
    address = _client_ip(request)
    now = monotonic()
    with _lock:
        events = _registration_attempts[address]
        _prune(events, now, _REGISTRATION_WINDOW_SECONDS)
        if len(events) >= _MAX_REGISTRATIONS:
            retry_after = max(1, int(_REGISTRATION_WINDOW_SECONDS - (now - events[0])))
            raise HTTPException(
                status_code=429,
                detail="Too many registration attempts. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        events.append(now)
