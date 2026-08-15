"""Public, rate-limited Bethel website assistant.

The OpenAI API key is used only server-side. When AI is unavailable or the
question is outside the supported public-information scope, the assistant
returns the public support email instead of guessing.
"""
from __future__ import annotations

from collections import defaultdict, deque
import os
from threading import Lock
from time import monotonic

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/public/assistant", tags=["Public Website Assistant"])

SUPPORT_EMAIL = os.getenv("PUBLIC_SUPPORT_EMAIL", "info@betheltradingtechnologies.com").strip()
OPENAI_MODEL = os.getenv("BETHEL_ASSISTANT_MODEL", "gpt-5.6").strip()
WINDOW_SECONDS = 600
MAX_REQUESTS = 20
_attempts: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()

PUBLIC_FACTS = """
Bethel Trading Technologies develops algorithmic trading technology, copy-trading technology,
financial analytics and risk-management technology. The public website is
https://betheltradingtechnologies.com. Visitors can register through the website's Register Now
link and then follow the subscriber onboarding process. Identity verification is handled through
Bethel Native KYC. The platform may display read-only MT5 telemetry and verified-performance
links when those public features are enabled. Bethel does not promise or guarantee investment
returns. Trading foreign exchange, CFDs and leveraged products involves significant risk and past
performance does not guarantee future results. General support email: {support_email}.
""".strip().format(support_email=SUPPORT_EMAIL)

INSTRUCTIONS = f"""
You are the public website assistant for Bethel Trading Technologies.
Answer brief visitor questions clearly, politely and concisely using ONLY the verified public facts
below and information explicitly contained in the visitor's question. Never invent fees, returns,
licences, regulator approvals, account status, staff details, broker terms or technical/internal
security details. Never provide personalized financial, investment or trading advice. Never promise
returns. Do not request passwords, API keys, seed phrases, card details, identity documents or other
secrets. If a question requires account-specific help, private records, a human decision, or facts not
listed below, say you cannot confirm that information and direct the visitor to {SUPPORT_EMAIL}.
If the visitor asks how to contact Bethel, provide {SUPPORT_EMAIL}. Keep answers under 120 words.

VERIFIED PUBLIC FACTS:
{PUBLIC_FACTS}
""".strip()


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class AssistantResponse(BaseModel):
    answer: str
    support_email: str
    ai_available: bool


def _client_ip(request: Request) -> str:
    return (
        (request.headers.get("cf-connecting-ip") or "").strip()
        or (request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
        or (request.client.host if request.client else "unknown")
    )[:64]


def _check_rate_limit(request: Request) -> None:
    now = monotonic()
    key = _client_ip(request)
    with _lock:
        events = _attempts[key]
        while events and now - events[0] >= WINDOW_SECONDS:
            events.popleft()
        if len(events) >= MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail=f"Too many chat requests. Please try again later or email {SUPPORT_EMAIL}.",
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )
        events.append(now)


def _fallback(message: str) -> str:
    lowered = message.casefold()
    if any(word in lowered for word in ("email", "contact", "support", "help", "reach")):
        return f"You can contact Bethel Trading Technologies at {SUPPORT_EMAIL}."
    if "kyc" in lowered or "identity" in lowered or "verify" in lowered:
        return (
            "Bethel uses its Native KYC process for identity verification. For help with a specific "
            f"verification or account, please email {SUPPORT_EMAIL}."
        )
    if "register" in lowered or "sign up" in lowered or "signup" in lowered or "join" in lowered:
        return (
            "You can start from the Register Now link on the Bethel website and follow the subscriber "
            f"onboarding steps. If you need help, email {SUPPORT_EMAIL}."
        )
    if "return" in lowered or "profit" in lowered or "guarantee" in lowered or "investment advice" in lowered:
        return (
            "Bethel does not guarantee investment returns, and the website assistant cannot provide "
            f"personalized financial advice. For general company questions, email {SUPPORT_EMAIL}."
        )
    if "what is bethel" in lowered or "what does bethel" in lowered or "service" in lowered:
        return (
            "Bethel Trading Technologies develops algorithmic trading, copy-trading, financial analytics "
            "and risk-management technology."
        )
    return f"I can't confirm that from the public information available to me. Please email {SUPPORT_EMAIL} for help."


def _extract_text(payload: dict) -> str:
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") in {"output_text", "text"} and part.get("text"):
                return str(part["text"]).strip()
    return ""


@router.post("/chat", response_model=AssistantResponse)
def public_chat(data: AssistantRequest, request: Request):
    _check_rate_limit(request)
    message = data.message.strip()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return AssistantResponse(answer=_fallback(message), support_email=SUPPORT_EMAIL, ai_available=False)

    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "instructions": INSTRUCTIONS,
                "input": message,
                "max_output_tokens": 220,
            },
            timeout=25,
        )
        response.raise_for_status()
        answer = _extract_text(response.json())
        if not answer:
            raise ValueError("empty assistant response")
        return AssistantResponse(answer=answer, support_email=SUPPORT_EMAIL, ai_available=True)
    except Exception:
        return AssistantResponse(answer=_fallback(message), support_email=SUPPORT_EMAIL, ai_available=False)
