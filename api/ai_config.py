"""Central, secret-safe AI feature configuration for Bethel."""
from __future__ import annotations

import os


def _enabled(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def provider_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def feature_status() -> dict[str, bool]:
    return {
        "public_assistant": _enabled("BETHEL_AI_PUBLIC_ASSISTANT_ENABLED", True),
        "daily_market_brief": _enabled("DAILY_MARKET_BRIEF_AI_ENABLED"),
        "performance_commentary": _enabled("BETHEL_AI_PERFORMANCE_COMMENTARY_ENABLED"),
        "support_drafts": _enabled("BETHEL_AI_SUPPORT_DRAFTS_ENABLED"),
        "market_summary": _enabled("BETHEL_AI_MARKET_SUMMARY_ENABLED"),
        "social_content": _enabled("BETHEL_AI_SOCIAL_CONTENT_ENABLED"),
        "investor_reports": _enabled("BETHEL_AI_INVESTOR_REPORTS_ENABLED"),
        "document_summary": _enabled("BETHEL_AI_DOCUMENT_SUMMARY_ENABLED"),
        "internal_assistant": _enabled("BETHEL_AI_INTERNAL_ASSISTANT_ENABLED"),
        "transcription": _enabled("BETHEL_AI_TRANSCRIPTION_ENABLED"),
        "image_generation": _enabled("BETHEL_AI_IMAGE_GENERATION_ENABLED"),
    }


def safe_status() -> dict:
    """Return runtime AI readiness without returning any secret value."""
    return {
        "provider": "openai",
        "provider_configured": provider_configured(),
        "features": feature_status(),
    }
