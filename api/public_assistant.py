"""Public, rate-limited Bethel website assistant.

The OpenAI API key is used only server-side. The assistant is limited to
approved public information and every response is forced to include the public
support email for human follow-up.
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
OPENAI_MODEL = os.getenv("BETHEL_ASSISTANT_MODEL", "gpt-5.6-luna").strip()
WINDOW_SECONDS = int(os.getenv("BETHEL_ASSISTANT_WINDOW_SECONDS", "3600"))
MAX_REQUESTS = int(os.getenv("BETHEL_ASSISTANT_MAX_REQUESTS_PER_WINDOW", "8"))
MAX_MESSAGE_CHARS = int(os.getenv("BETHEL_ASSISTANT_MAX_MESSAGE_CHARS", "500"))
MAX_OUTPUT_TOKENS = int(os.getenv("BETHEL_ASSISTANT_MAX_OUTPUT_TOKENS", "140"))
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
listed below, say you cannot confirm that information. Do not reveal internal architecture, database
information, credentials, KYC evidence, customer records, admin records, proprietary trading logic,
or private project information. Keep the informational portion under 80 words. The server will append
the official support email to every response.

VERIFIED PUBLIC FACTS:
{PUBLIC_FACTS}
""".strip()


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class AssistantResponse(BaseModel):
    answer: str
    support_email: str
    ai_available: bool


def _with_support_email(answer: str) -> str:
    text = (answer or "").strip()
    footer = f"For further inquiries, email: {SUPPORT_EMAIL}"
    if SUPPORT_EMAIL.casefold() in text.casefold():
        return text
    if not text:
        return footer
    return f"{text}\n\n{footer}"


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
                detail=f"Chat limit reached for this visitor. For further inquiries, email: {SUPPORT_EMAIL}",
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )
        events.append(now)


def _fallback(message: str) -> str:
    lowered = message.casefold()
    if any(word in lowered for word in ("email", "contact", "support", "help", "reach")):
        return "You can contact Bethel Trading Technologies using the inquiry email below."
    if "kyc" in lowered or "identity" in lowered or "verify" in lowered:
        return "Bethel uses its Native KYC process for identity verification. Account-specific verification questions require human support."
    if "register" in lowered or "sign up" in lowered or "signup" in lowered or "join" in lowered:
        return "You can start from the Register Now link on the Bethel website and follow the subscriber onboarding steps."
    if "return" in lowered or "profit" in lowered or "guarantee" in lowered or "investment advice" in lowered:
        return "Bethel does not guarantee investment returns, and the website assistant cannot provide personalized financial advice."
    if "what is bethel" in lowered or "what does bethel" in lowered or "service" in lowered:
        return "Bethel Trading Technologies develops algorithmic trading, copy-trading, financial analytics and risk-management technology."
    return "I can't confirm that from the approved public information available to me."


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
        return AssistantResponse(answer=_with_support_email(_fallback(message)), support_email=SUPPORT_EMAIL, ai_available=False)

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
                "max_output_tokens": MAX_OUTPUT_TOKENS,
            },
            timeout=20,
        )
        response.raise_for_status()
        answer = _extract_text(response.json())
        if not answer:
            raise ValueError("empty assistant response")
        return AssistantResponse(answer=_with_support_email(answer), support_email=SUPPORT_EMAIL, ai_available=True)
    except Exception:
        return AssistantResponse(answer=_with_support_email(_fallback(message)), support_email=SUPPORT_EMAIL, ai_available=False)
