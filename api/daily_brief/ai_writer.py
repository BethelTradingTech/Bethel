"""Fail-safe AI editorial writer for Bethel Daily Market Brief.

The writer is deliberately isolated from MT5 and CopyHub. It receives only
already-collected public market headlines and Bethel's read-only public snapshot.
If AI is disabled, unavailable, times out, or returns invalid content, callers
must continue with the existing deterministic RSS renderer.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.6-luna"


@dataclass(frozen=True)
class AIBrief:
    headline: str
    body: str
    social_text: str
    model: str


def ai_generation_enabled() -> bool:
    return os.getenv("DAILY_MARKET_BRIEF_AI_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _extract_text(payload: dict[str, Any]) -> str:
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") in {"output_text", "text"} and part.get("text"):
                return str(part["text"]).strip()
    return ""


def _strip_json_fence(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    return value


def _source_appendix(headlines: list[dict[str, str]]) -> str:
    lines = ["SOURCES"]
    for item in headlines:
        title = str(item.get("title", "")).strip()
        source = str(item.get("source", "")).strip()
        url = str(item.get("url", "")).strip()
        if title and source and url.startswith("https://"):
            lines.append(f"- {source}: {title} — {url}")
    return "\n".join(lines)


def _safe_openai_error_code(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return "unknown"
    if not isinstance(payload, dict):
        return "unknown"
    error = payload.get("error")
    if not isinstance(error, dict):
        return "unknown"
    value = error.get("code") or error.get("type")
    if value is None:
        return "unknown"
    text = str(value).strip().lower()
    safe = "".join(ch for ch in text if ch.isalnum() or ch in {"_", "-"})
    return safe[:80] or "unknown"


def generate_ai_brief(
    headlines: list[dict[str, str]],
    snapshot: dict[str, Any],
    feed_errors: list[str],
    now: datetime,
) -> AIBrief | None:
    """Return a validated AI brief, or None so the caller can use RSS fallback."""
    if not ai_generation_enabled():
        print("Daily Market Brief AI diagnostic: skipped=disabled")
        return None

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("Daily Market Brief AI diagnostic: skipped=missing_api_key")
        return None

    model = os.getenv(
        "DAILY_MARKET_BRIEF_AI_MODEL",
        os.getenv("BETHEL_ASSISTANT_MODEL", DEFAULT_MODEL),
    ).strip() or DEFAULT_MODEL
    timeout = max(5, min(45, int(os.getenv("DAILY_MARKET_BRIEF_AI_TIMEOUT_SECONDS", "25"))))
    max_output_tokens = max(500, min(3000, int(os.getenv("DAILY_MARKET_BRIEF_AI_MAX_OUTPUT_TOKENS", "1600"))))

    evidence = {
        "brief_date_utc": now.date().isoformat(),
        "headlines": headlines,
        "bethel_public_snapshot": snapshot,
        "feed_error_count": len(feed_errors),
    }
    instructions = """
You are the editorial engine for Bethel Trading Technologies' Daily Market Close.
Use ONLY the evidence supplied in the input. Do not browse, invent prices, invent
percentage moves, infer an unreported market close, or claim a cause that is not
supported by the supplied headlines. Clearly distinguish reported facts from
careful interpretation. Focus on major market developments relevant to global
markets, especially gold, FX, indices and macro drivers when they are present in
the evidence. Do not provide personalized investment advice, trade signals,
guaranteed returns or promises. Do not expose internal systems or credentials.

Return ONLY valid JSON with exactly these string fields:
{"headline":"...","body":"...","social_text":"..."}

The body should be a concise, publication-ready market-close report with a short
opening, key developments, main drivers, what to watch next, and this disclaimer:
"Market information is provided for general informational purposes only and is not investment advice. Past performance does not guarantee future results."
Do not include source URLs in the body; the server appends a verified source list.
The social_text must be concise, factual and suitable for public social channels.
""".strip()

    try:
        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "instructions": instructions,
                "input": json.dumps(evidence, sort_keys=True, default=str),
                "max_output_tokens": max_output_tokens,
            },
            timeout=timeout,
        )
        if not response.ok:
            print(
                "Daily Market Brief AI diagnostic: "
                f"failed=http_{response.status_code}; code={_safe_openai_error_code(response)}"
            )
            return None

        try:
            response_payload = response.json()
        except ValueError:
            print("Daily Market Brief AI diagnostic: failed=invalid_response_json")
            return None

        text = _extract_text(response_payload)
        if not text:
            print("Daily Market Brief AI diagnostic: failed=empty_output")
            return None
        try:
            payload = json.loads(_strip_json_fence(text))
        except (TypeError, ValueError):
            print("Daily Market Brief AI diagnostic: failed=invalid_model_json")
            return None
        if not isinstance(payload, dict):
            print("Daily Market Brief AI diagnostic: failed=unexpected_model_payload")
            return None

        headline = str(payload.get("headline", "")).strip()
        body = str(payload.get("body", "")).strip()
        social_text = str(payload.get("social_text", "")).strip()
        if not (5 <= len(headline) <= 240):
            print("Daily Market Brief AI diagnostic: failed=headline_validation")
            return None
        if not (80 <= len(body) <= 18000):
            print("Daily Market Brief AI diagnostic: failed=body_validation")
            return None
        if not (20 <= len(social_text) <= 4500):
            print("Daily Market Brief AI diagnostic: failed=social_validation")
            return None

        appendix = _source_appendix(headlines)
        if len(appendix.splitlines()) > 1:
            body = f"{body}\n\n{appendix}"
        print(f"Daily Market Brief AI diagnostic: success; model={model}")
        return AIBrief(headline=headline, body=body, social_text=social_text, model=model)
    except requests.Timeout:
        print("Daily Market Brief AI diagnostic: failed=timeout")
        return None
    except requests.RequestException as exc:
        print(f"Daily Market Brief AI diagnostic: failed=request_{type(exc).__name__}")
        return None
    except Exception as exc:
        print(f"Daily Market Brief AI diagnostic: failed=unexpected_{type(exc).__name__}")
        return None
