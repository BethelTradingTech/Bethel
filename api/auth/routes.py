"""Legacy administrator login compatibility route.

This route is intentionally disabled. Bethel's supported administrator login is
/api/auth/routes/auth.py at POST /auth/login, which uses database-backed users,
login throttling, and secure cookies.
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(include_in_schema=False)


@router.post("/login")
def legacy_login_disabled():
    raise HTTPException(
        status_code=410,
        detail="Legacy administrator login is disabled. Use /auth/login.",
    )
