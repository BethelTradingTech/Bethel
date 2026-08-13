"""Explainable decision-support scoring for Bethel Native KYC.

This module deliberately does not make the legal/compliance decision. It turns
recorded verification checks into a reproducible confidence score and a
recommendation for an authorized reviewer. Missing biometric/OCR checks reduce
confidence and can never be hidden by other passing checks.
"""

from __future__ import annotations


WEIGHTS = {
    "document": 0.08,
    "malware": 0.05,
    "authenticity": 0.17,
    "ocr": 0.10,
    "field_match": 0.13,
    "liveness": 0.18,
    "face_match": 0.19,
    "sanctions": 0.10,
}

SECURITY_HARD_FAILS = {"malware", "authenticity", "liveness", "face_match", "sanctions"}
REQUIRED_AUTOMATED = {"authenticity", "ocr", "field_match", "liveness", "face_match", "sanctions"}


def _status_score(row) -> float | None:
    if row is None:
        return None
    status = str(getattr(row, "status", "") or "").lower()
    raw_score = getattr(row, "score", None)
    if status == "passed":
        if raw_score is None:
            return 100.0
        return max(0.0, min(100.0, float(raw_score)))
    if status == "failed":
        return 0.0
    if status == "review":
        if raw_score is None:
            return 50.0
        return max(0.0, min(100.0, float(raw_score)))
    return None


def assisted_assessment(checks: dict) -> dict:
    weighted_points = 0.0
    total_weight = sum(WEIGHTS.values())
    available_weight = 0.0
    unavailable = []
    failed = []
    review = []
    components = {}

    for name, weight in WEIGHTS.items():
        row = checks.get(name)
        value = _status_score(row)
        status = str(getattr(row, "status", "not_available") or "not_available").lower() if row else "not_available"
        reasons = list(getattr(row, "reasons", None) or []) if row else ["No recorded result"]
        components[name] = {"status": status, "score": value, "weight_percent": round(weight * 100, 1), "reasons": reasons}
        if value is None:
            unavailable.append(name)
            continue
        available_weight += weight
        weighted_points += weight * value
        if status == "failed":
            failed.append(name)
        elif status == "review":
            review.append(name)

    # Missing checks contribute zero to the overall confidence. Coverage is
    # separately exposed so a reviewer can distinguish weak evidence from a
    # genuine negative result.
    confidence = round(weighted_points / total_weight, 2) if total_weight else 0.0
    coverage = round((available_weight / total_weight) * 100, 2) if total_weight else 0.0
    hard_fail = sorted(SECURITY_HARD_FAILS.intersection(failed))
    required_missing = sorted(REQUIRED_AUTOMATED.intersection(unavailable))

    if hard_fail:
        recommendation = "REJECT_OR_ESCALATE"
        rationale = "One or more security-critical identity checks failed."
    elif required_missing:
        recommendation = "MANUAL_REVIEW_REQUIRED"
        rationale = "Required automated identity checks are unavailable; do not auto-approve."
    elif review or confidence < 85:
        recommendation = "MANUAL_REVIEW_REQUIRED"
        rationale = "Automated evidence is incomplete, ambiguous, or below the assisted-approval threshold."
    else:
        recommendation = "ELIGIBLE_FOR_COMPLIANCE_APPROVAL"
        rationale = "Automated identity evidence is complete and meets the assisted-review threshold; final approval remains with Compliance."

    return {
        "model": "bethel-explainable-kyc-assist-v1",
        "confidence_score": confidence,
        "evidence_coverage_score": coverage,
        "recommendation": recommendation,
        "rationale": rationale,
        "auto_decision": False,
        "final_decision_owner": "authorized_compliance_officer",
        "unavailable_checks": sorted(unavailable),
        "failed_checks": sorted(failed),
        "review_checks": sorted(review),
        "components": components,
        "thresholds": {"assisted_approval_confidence": 85.0, "required_coverage": 100.0},
    }
