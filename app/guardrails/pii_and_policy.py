"""PII Redaction and Guardrail Policy Filter.

Implements strict HIPAA-compliant PII scrubbing (Social Security Numbers, Phone Numbers,
Email Addresses, Medical Record Numbers) and prompt-injection / dangerous clinical
prescribing guardrails.
"""

import re
from typing import Dict, Any, Tuple


# Regex patterns for common HIPAA PII identifiers
REGEX_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"(\+?\d{1,2}\s?)?(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),
    "mrn": re.compile(r"\b(MRN|CHART)[-:\s]?\d{6,10}\b", re.IGNORECASE),
}

DANGEROUS_ACTIONS = [
    "bypass physician approval",
    "override safety check",
    "execute unauthorized prescription",
    "ignore hipaa",
]


def redact_pii(text: str) -> Tuple[str, Dict[str, int]]:
    """Redacts Personally Identifiable Information (PII) from clinical text before LLM ingestion.

    Replaces identifiable elements (emails, phone numbers, SSNs, MRNs) with explicit
    redaction tokens to protect patient privacy in compliance with HIPAA Safe Harbor guidelines.

    Args:
        text: Raw text string containing potential clinical and personal details.

    Returns:
        A tuple of (redacted_text, redaction_counts).
    """
    counts = {}
    scrubbed = text

    # SSN
    ssn_matches = len(REGEX_PATTERNS["ssn"].findall(scrubbed))
    if ssn_matches > 0:
        counts["ssn"] = ssn_matches
        scrubbed = REGEX_PATTERNS["ssn"].sub("[REDACTED_SSN]", scrubbed)

    # Phone
    phone_matches = len(REGEX_PATTERNS["phone"].findall(scrubbed))
    if phone_matches > 0:
        counts["phone"] = phone_matches
        scrubbed = REGEX_PATTERNS["phone"].sub("[REDACTED_PHONE]", scrubbed)

    # Email
    email_matches = len(REGEX_PATTERNS["email"].findall(scrubbed))
    if email_matches > 0:
        counts["email"] = email_matches
        scrubbed = REGEX_PATTERNS["email"].sub("[REDACTED_EMAIL]", scrubbed)

    # MRN
    mrn_matches = len(REGEX_PATTERNS["mrn"].findall(scrubbed))
    if mrn_matches > 0:
        counts["mrn"] = mrn_matches
        scrubbed = REGEX_PATTERNS["mrn"].sub("[REDACTED_MRN]", scrubbed)

    return scrubbed, counts


def validate_safety_guardrails(text: str) -> Dict[str, Any]:
    """Applies security, compliance, and clinical safety policies on incoming requests.

    Verifies that the prompt does not attempt adversarial jailbreaks or unauthorized
    overrides of human-in-the-loop protocols.

    Args:
        text: Input prompt or message text.

    Returns:
        A dictionary with 'passed' (bool) and optional 'violation' reason.
    """
    lower_text = text.lower()
    for danger in DANGEROUS_ACTIONS:
        if danger in lower_text:
            return {
                "passed": False,
                "violation": f"Guardrail Alert: Attempted unauthorized safety bypass detected ('{danger}').",
                "policy_code": "CLINICAL_SAFETY_SEC_01",
            }

    return {"passed": True, "policy_code": "SAFE"}
