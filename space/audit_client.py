"""HTTP client for Modal audit endpoint with mock fallback."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from merge import parse_llm_json
from prompts import FEW_SHOT_ASSISTANT


def get_modal_url() -> str | None:
    return os.environ.get("MODAL_AUDIT_URL") or os.environ.get("MODAL_AUDIT_ENDPOINT")


def call_modal_audit(
    platform: str,
    goal: str,
    audience: str,
    post: str,
    *,
    timeout: float = 120.0,
) -> dict[str, Any]:
    url = get_modal_url()
    if not url:
        return _mock_llm_response(platform, goal, audience, post)

    payload = json.dumps(
        {
            "platform": platform,
            "goal": goal,
            "audience": audience,
            "post": post,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url.rstrip("/") + "/audit",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Modal HTTP {exc.code}: {body}") from exc

    if "raw" in data:
        return parse_llm_json(data["raw"])
    return data


def _mock_llm_response(
    platform: str,
    goal: str,
    audience: str,
    post: str,
) -> dict[str, Any]:
    """Deterministic mock when Modal URL is unset — uses few-shot shape for webinar-like posts."""
    del platform, goal, audience
    lower = post.lower()
    if "link in bio" in lower or "webinar" in lower:
        return json.loads(FEW_SHOT_ASSISTANT)
    return {
        "briefCheck": {
            "status": "ok",
            "inferred": {
                "goal": "Unclear from post — needs editor review",
                "audience": "In-context colleagues",
            },
            "gaps": [],
        },
        "auditReport": {
            "goalAlignment": {
                "overall": 40,
                "cappedBy": [],
                "dimensions": [
                    {"key": "hook", "score": 2, "rationale": "Opening lacks a clear stake or benefit."},
                    {"key": "clarity", "score": 2, "rationale": "Multiple topics mixed in one dump."},
                    {"key": "audienceFit", "score": 3, "rationale": "Jargon may fit insiders but structure is rough."},
                    {"key": "goalService", "score": 2, "rationale": "Does not clearly drive the stated goal actions."},
                    {"key": "cta", "score": 2, "rationale": "Call to action is logistics-only or missing deadline."},
                ],
                "summary": "Mock audit (set MODAL_AUDIT_URL for live Gemma 4 E4B). Post needs structure and a clearer CTA.",
            },
            "warnings": [
                {
                    "code": "MIXED_MESSAGES",
                    "severity": "warning",
                    "source": "llm",
                    "message": "Artifact, task, and logistics appear mixed.",
                },
                {
                    "code": "NO_CLEAR_CTA",
                    "severity": "warning",
                    "source": "llm",
                    "message": "No explicit personal action with a deadline.",
                },
            ],
            "rewriteHints": [
                "Lead with why the reader should act now.",
                "Separate artifact, task, and logistics into sections.",
                "Add one explicit CTA with a deadline.",
            ],
        },
    }
