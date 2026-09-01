"""Central, secret-safe AI feature configuration for Bethel."""
from __future__ import annotations

import os

FEATURE_ENV_VARS = {
    "public_assistant": "BETHEL_AI_PUBLIC_ASSISTANT_ENABLED",
    "daily_market_brief": "DAILY_MARKET_BRIEF_AI_ENABLED",
    "performance_commentary": "BETHEL_AI_PERFORMANCE_COMMENTARY_ENABLED",
    "support_drafts": "BETHEL_AI_SUPPORT_DRAFTS_ENABLED",
    "market_summary": "BETHEL_AI_MARKET_SUMMARY_ENABLED",
    "social_content": "BETHEL_AI_SOCIAL_CONTENT_ENABLED",
    "investor_reports": "BETHEL_AI_INVESTOR_REPORTS_ENABLED",
    "document_summary": "BETHEL_AI_DOCUMENT_SUMMARY_ENABLED",
    "internal_assistant": "BETHEL_AI_INTERNAL_ASSISTANT_ENABLED",
    "transcription": "BETHEL_AI_TRANSCRIPTION_ENABLED",
    "image_generation": "BETHEL_AI_IMAGE_GENERATION_ENABLED",
}


def _enabled(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def provider_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def feature_enabled(feature: str) -> bool:
    env_name = FEATURE_ENV_VARS.get(feature)
    if not env_name:
        return False
    return _enabled(env_name, default=(feature == "public_assistant"))


def feature_status() -> dict[str, bool]:
    return {name: feature_enabled(name) for name in FEATURE_ENV_VARS}


def safe_status() -> dict:
    """Return runtime AI readiness without returning any secret value."""
    return {
        "provider": "openai",
        "provider_configured": provider_configured(),
        "default_model": os.getenv("BETHEL_AI_DEFAULT_MODEL", os.getenv("BETHEL_ASSISTANT_MODEL", "gpt-5.6-luna")).strip() or "gpt-5.6-luna",
        "features": feature_status(),
    }
