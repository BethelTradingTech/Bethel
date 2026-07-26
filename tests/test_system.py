"""
Bethel Trading Technologies API smoke test.

Run while the API is available at http://127.0.0.1:8000.
Set BETHEL_ADMIN_EMAIL and BETHEL_ADMIN_PASSWORD to include protected routes.
"""

import os
import sys

import requests


API = os.getenv("BETHEL_API_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = 15


def request(method, endpoint, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.request(
        method,
        API + endpoint,
        headers=headers,
        timeout=TIMEOUT,
        allow_redirects=False,
        **kwargs,
    )


def main():
    failures = []

    public_checks = [
        ("/", 200),
        ("/health", 200),
        ("/openapi.json", 200),
        ("/investor/api/mt5", 200),
        ("/performance/equity-history", 200),
        ("/performance/analytics", 200),
        ("/copytrading/dashboard", 200),
    ]

    for endpoint, expected in public_checks:
        response = request("GET", endpoint)
        print(f"{endpoint}: {response.status_code}")
        if response.status_code != expected:
            failures.append(
                f"{endpoint}: expected {expected}, got {response.status_code}"
            )

    email = os.getenv("BETHEL_ADMIN_EMAIL")
    password = os.getenv("BETHEL_ADMIN_PASSWORD")

    if email and password:
        login = request(
            "POST",
            "/auth/login",
            params={"email": email, "password": password},
        )

        if login.status_code != 200:
            failures.append(f"/auth/login: expected 200, got {login.status_code}")
        else:
            token = login.json()["access_token"]
            for endpoint in ("/dashboard/data", "/mt5/account", "/mt5/positions"):
                response = request("GET", endpoint, token=token)
                print(f"{endpoint}: {response.status_code}")
                if response.status_code != 200:
                    failures.append(
                        f"{endpoint}: expected 200, got {response.status_code}"
                    )
    else:
        print("Protected checks skipped: admin environment variables are not set")

    if failures:
        print("\nFAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nAll requested API smoke checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
