"""Merge LLM output with rule warnings and recompute scores."""

from __future__ import annotations

import json
from typing import Any


DIMENSION_KEYS = ("hook", "clarity", "audienceFit", "goalService", "cta")


def parse_llm_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output")
    return json.loads(text[start : end + 1])


def recompute_overall(dimensions: list[dict[str, Any]], capped_by: list[str]) -> int:
    scores = [int(d.get("score", 0)) for d in dimensions if d.get("key") in DIMENSION_KEYS]
    if not scores:
        return 0
    overall = round(sum(scores) / len(scores) / 5 * 100)
    if capped_by:
        overall = min(overall, 39)
    return overall


def merge_warnings(
    llm_warnings: list[dict[str, Any]],
    rule_warnings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_code: dict[str, dict[str, Any]] = {}
    for w in llm_warnings:
        code = w.get("code")
        if code:
            by_code[code] = w
    for w in rule_warnings:
        code = w.get("code")
        if code:
            by_code[code] = w  # rule wins on conflict
    return list(by_code.values())


def capped_by_from_warnings(warnings: list[dict[str, Any]]) -> list[str]:
    return sorted({w["code"] for w in warnings if w.get("severity") == "critical" and w.get("code")})


def merge_audit(
    llm_payload: dict[str, Any],
    rule_warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    brief = llm_payload.get("briefCheck") or {}
    status = brief.get("status", "ok")

    if status == "needs_clarification":
        return {"briefCheck": brief, "auditReport": None}

    audit = llm_payload.get("auditReport")
    if not audit:
        return {"briefCheck": brief, "auditReport": None}

    ga = audit.get("goalAlignment") or {}
    dimensions = ga.get("dimensions") or []
    llm_warnings = audit.get("warnings") or audit.get("warnings_llm") or []
    rewrite_hints = audit.get("rewriteHints") or []

    warnings = merge_warnings(llm_warnings, rule_warnings)
    capped = capped_by_from_warnings(warnings)
    overall = recompute_overall(dimensions, capped)

    goal_alignment = {
        "overall": overall,
        "cappedBy": capped,
        "dimensions": dimensions,
        "summary": ga.get("summary") or "",
    }

    return {
        "briefCheck": brief,
        "auditReport": {
            "goalAlignment": goal_alignment,
            "warnings": warnings,
            "rewriteHints": rewrite_hints,
        },
    }


def viewer_payload(merged: dict[str, Any]) -> dict[str, Any]:
    """Flatten merged output for post-audit-viewer (audit section only)."""
    brief = merged.get("briefCheck")
    audit = merged.get("auditReport")
    if audit is None and brief:
        return brief
    if audit:
        return audit
    return merged
