"""Platform-specific thresholds for rule linters."""

HASHTAG_LIMITS = {
    "telegram": 3,
    "linkedin": 5,
    "x": 3,
    "twitter": 3,
    "other": 5,
}

ACTIVATING_GOAL_KEYWORDS = (
    "register",
    "sign up",
    "signup",
    "rsvp",
    "join",
    "attend",
    "apply",
    "submit",
    "deadline",
    "webinar",
    "event",
    "book",
    "buy",
    "donate",
    "vote",
    "enroll",
)

TIME_PATTERNS = (
    r"\b\d{1,2}[/:]\d{2}\b",
    r"\b\d{1,2}\s*(am|pm)\b",
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\b",
    r"\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\b",
    r"\bby\s+(tomorrow|tonight|eod|end of day)\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
)


def normalize_platform(platform: str) -> str:
    p = (platform or "other").strip().lower()
    if p in ("x/twitter", "x / twitter"):
        return "x"
    if p.startswith("twitter"):
        return "twitter"
    return p if p in HASHTAG_LIMITS else "other"


def hashtag_limit(platform: str) -> int:
    return HASHTAG_LIMITS.get(normalize_platform(platform), HASHTAG_LIMITS["other"])
