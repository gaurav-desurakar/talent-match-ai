import re

INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"ignore\s+(all\s+)?previous\s+instructions?",
        r"reveal\s+(the\s+)?(system\s+)?prompt",
        r"(?:give|assign|set)\s+(?:this\s+)?candidate\s+(?:a\s+)?(?:score\s+of\s+)?100",
        r"execute\s+(?:this\s+)?(?:shell\s+)?command",
        r"follow\s+these\s+instructions",
        r"system\s*:\s*you\s+are",
    )
)

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b(?:api[_-]?key|token|authorization)\s*[:=]\s*\S+", re.IGNORECASE),
)


def detect_prompt_injection(text: str, document_label: str) -> list[str]:
    """Return non-accusatory warnings without echoing suspicious document content."""
    if any(pattern.search(text) for pattern in INJECTION_PATTERNS):
        return [
            f"Potential instruction-like content detected in {document_label}; "
            "it was treated as document data and not followed."
        ]
    return []


def redact_secrets(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


IDENTITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)"),
    re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE),
)
PROTECTED_LINE_PATTERN = re.compile(
    r"^\s*(?:date of birth|dob|gender|sex|marital status|religion|nationality)\s*[:|-]",
    re.IGNORECASE,
)
PROTECTED_SCORING_PATTERN = re.compile(
    r"\b(?:age|date of birth|dob|race|ethnicity|gender|sex|marital status|religion|"
    r"nationality|pregnan(?:cy|t)|disabilit(?:y|ies)|sexual orientation)\b",
    re.IGNORECASE,
)


def contains_protected_scoring_attribute(text: str) -> bool:
    return PROTECTED_SCORING_PATTERN.search(text) is not None


def redact_resume_identity(text: str) -> str:
    """Remove direct identifiers before blind-review provider or scoring boundaries."""
    lines = text.splitlines()
    first_content_replaced = False
    output: list[str] = []
    for line in lines:
        if PROTECTED_LINE_PATTERN.search(line):
            output.append("[PROTECTED FIELD REDACTED]")
            continue
        redacted = line
        for pattern in IDENTITY_PATTERNS:
            redacted = pattern.sub("[CONTACT REDACTED]", redacted)
        if not first_content_replaced and redacted.strip():
            first_content_replaced = True
            if len(redacted.split()) <= 6 and not any(char.isdigit() for char in redacted):
                redacted = "[NAME REDACTED]"
        output.append(redacted)
    return "\n".join(output)
