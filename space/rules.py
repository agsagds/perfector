"""Deterministic rule-based warnings for social post audit."""

from __future__ import annotations

import re
from typing import Any

from platform_config import ACTIVATING_GOAL_KEYWORDS, TIME_PATTERNS, hashtag_limit, normalize_platform

URL_RE = re.compile(r"https?://\S+", re.I)
HASHTAG_RE = re.compile(r"#\w+", re.UNICODE)
CHAT_TIMESTAMP_RE = re.compile(
    r"\[\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}\s*(?:AM|PM)?\]",
    re.I,
)
CHAT_NAME_RE = re.compile(r"^\[[^\]]+\]\s+\w[\w\s.-]{0,40}:", re.M)
ENGAGEMENT_BAIT_RE = re.compile(
    r"\b(tag a friend|comment below|double tap|like and share|drop a .? below|"
    r"share this post|repost if you agree)\b",
    re.I,
)
STRUCTURE_MARKERS_RE = re.compile(
    r"(^[\s]*[-*•]\s|\n[\s]*[-*•]\s|^\d+\.\s|\n\d+\.\s|^#{1,3}\s|\*\*[^*]+\*\*)",
    re.M,
)


def detect_post_language(post: str) -> str:
    if not post.strip():
        return "en"
    cyrillic = sum(1 for c in post if "\u0400" <= c <= "\u04FF")
    return "ru" if cyrillic > len(post) * 0.15 else "en"


def _msg(lang: str, en: str, ru: str) -> str:
    return ru if lang == "ru" else en


def _warning(
    code: str,
    severity: str,
    message: str,
    evidence: str | None = None,
) -> dict[str, Any]:
    w: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "source": "rule",
        "message": message,
    }
    if evidence:
        w["evidence"] = evidence[:120]
    return w


def _first_line(post: str) -> str:
    lines = [ln.strip() for ln in post.strip().splitlines() if ln.strip()]
    return lines[0] if lines else ""


def _evidence_snippet(text: str, max_words: int = 12) -> str:
    words = text.split()
    return " ".join(words[:max_words])


def _goal_is_activating(goal: str) -> bool:
    g = goal.lower()
    return any(kw in g for kw in ACTIVATING_GOAL_KEYWORDS)


def _post_has_deadline(post: str) -> bool:
    for pat in TIME_PATTERNS:
        if re.search(pat, post, re.I):
            return True
    return False


def _check_hashtag_stuffing(post: str, platform: str, lang: str) -> dict[str, Any] | None:
    tags = HASHTAG_RE.findall(post)
    limit = hashtag_limit(platform)
    if len(tags) <= limit:
        return None
    return _warning(
        "HASHTAG_STUFFING",
        "warning",
        _msg(
            lang,
            f"{len(tags)} hashtags exceed the {normalize_platform(platform)} limit ({limit}).",
            f"{len(tags)} хэштегов — больше порога для {normalize_platform(platform)} ({limit}).",
        ),
        _evidence_snippet(" ".join(tags[:6])),
    )


def _check_chat_dump(post: str, lang: str) -> dict[str, Any] | None:
    m = CHAT_TIMESTAMP_RE.search(post) or CHAT_NAME_RE.search(post)
    if not m:
        return None
    return _warning(
        "CHAT_DUMP_FORMAT",
        "warning",
        _msg(
            lang,
            "Timestamps or chat-style name prefixes look like a pasted conversation, not a composed post.",
            "Таймстемпы и подписи «Имя:» — похоже на копипаст чата, а не собранный пост.",
        ),
        _evidence_snippet(m.group(0)),
    )


def _check_weak_opening(post: str, lang: str) -> dict[str, Any] | None:
    first = _first_line(post)
    if not first:
        return None
    if URL_RE.fullmatch(first.strip()) or (
        URL_RE.search(first) and len(first.split()) <= 4
    ):
        return _warning(
            "WEAK_OPENING",
            "warning",
            _msg(
                lang,
                "First line is a bare link or too thin to hook the reader.",
                "Первая строка — голая ссылка или слабая зацепка.",
            ),
            _evidence_snippet(first),
        )
    return None


def _check_wall_of_text(post: str, lang: str) -> dict[str, Any] | None:
    for para in post.split("\n\n"):
        p = para.strip()
        if len(p) > 400 and "\n" not in p:
            return _warning(
                "WALL_OF_TEXT",
                "warning",
                _msg(
                    lang,
                    "Long paragraph without line breaks is hard to scan.",
                    "Длинный абзац без переносов — тяжело читать.",
                ),
                _evidence_snippet(p),
            )
    return None


def _check_no_structure(post: str, lang: str) -> dict[str, Any] | None:
    if len(post) < 280:
        return None
    if STRUCTURE_MARKERS_RE.search(post):
        return None
    if post.count("\n") >= 4:
        return None
    return _warning(
        "NO_STRUCTURE",
        "warning",
        _msg(
            lang,
            "Long post lacks bullets, numbers, or headings — reads as a flat dump.",
            "Длинный пост без списков и иерархии — плоский дамп.",
        ),
        _evidence_snippet(_first_line(post) or post[:80]),
    )


def _check_engagement_bait(post: str, lang: str) -> dict[str, Any] | None:
    m = ENGAGEMENT_BAIT_RE.search(post)
    if not m:
        return None
    return _warning(
        "ENGAGEMENT_BAIT",
        "warning",
        _msg(
            lang,
            "Engagement-bait phrasing detected.",
            "Обнаружена «приманка» для вовлечения.",
        ),
        _evidence_snippet(m.group(0)),
    )


def _check_bare_link(post: str, lang: str) -> dict[str, Any] | None:
    urls = URL_RE.findall(post)
    if not urls:
        return None
    for url in urls:
        idx = post.find(url)
        before = post[max(0, idx - 80) : idx].strip()
        after = post[idx + len(url) : idx + len(url) + 80].strip()
        context = (before + " " + after).strip()
        if len(context.split()) < 6:
            return _warning(
                "BARE_LINK",
                "info",
                _msg(
                    lang,
                    "Link appears without framing — say what's inside and why to open it.",
                    "Ссылка без рамки — неясно, что внутри и зачем открывать.",
                ),
                _evidence_snippet(url),
            )
    return None


def _check_dense_parenthetical(post: str, lang: str) -> dict[str, Any] | None:
    for m in re.finditer(r"\([^)]{80,}\)", post):
        return _warning(
            "DENSE_PARENTHETICAL",
            "info",
            _msg(
                lang,
                "Long parenthetical breaks reading flow.",
                "Длинная вставка в скобках тормозит чтение.",
            ),
            _evidence_snippet(m.group(0)),
        )
    return None


def _check_no_deadline(post: str, goal: str, lang: str) -> dict[str, Any] | None:
    if not _goal_is_activating(goal):
        return None
    if _post_has_deadline(post):
        return None
    return _warning(
        "NO_DEADLINE",
        "warning",
        _msg(
            lang,
            "Goal implies a time-bound action, but the post has no date or deadline.",
            "Цель требует действия ко времени, но в посте нет срока.",
        ),
        _evidence_snippet(_first_line(post) or post[:60]),
    )


def _check_unresolved_reference(post: str, lang: str) -> dict[str, Any] | None:
    refs = re.search(
        r"\b(link in bio|link in profile|see profile|check my profile|"
        r"registration link|sign up link)\b",
        post,
        re.I,
    )
    if not refs:
        return None
    if URL_RE.search(post):
        return None
    return _warning(
        "UNRESOLVED_REFERENCE",
        "info",
        _msg(
            lang,
            "Registration or resource is referenced but no URL is in the post.",
            "Регистрация упомянута, но ссылки в тексте нет.",
        ),
        _evidence_snippet(refs.group(0)),
    )


def run_rules(
    platform: str,
    goal: str,
    audience: str,
    post: str,
) -> list[dict[str, Any]]:
    """Run all rule linters and return warning objects."""
    del audience  # reserved for future rule checks
    lang = detect_post_language(post)
    checks = [
        _check_hashtag_stuffing(post, platform, lang),
        _check_chat_dump(post, lang),
        _check_weak_opening(post, lang),
        _check_wall_of_text(post, lang),
        _check_no_structure(post, lang),
        _check_engagement_bait(post, lang),
        _check_bare_link(post, lang),
        _check_dense_parenthetical(post, lang),
        _check_no_deadline(post, goal, lang),
        _check_unresolved_reference(post, lang),
    ]
    return [w for w in checks if w is not None]
