"""LLM prompts for post audit (LLM-judgment codes only)."""

from __future__ import annotations

from platform_config import hashtag_limit, normalize_platform

SYSTEM_PROMPT = """You are a social media editor. Audit the post against the stated goal and audience. Return STRICTLY valid JSON matching the schema below.
No text outside JSON: no preamble, no markdown fences, no comments. Response starts with { and ends with }.

INPUT (in the user message): platform, goal, audience, post.

STEP 0 — brief check (briefCheck).
- Goal is verifiable if there is an observable outcome and direction (not vague "engagement" but a concrete action or result).
- Audience is verifiable if role/level/context is clear (not "everyone" or "professionals").
- Always output inferred.goal and inferred.audience from the post text — your interpretation even if the brief is fine.
- If a brief field is vague, add a gaps object: field ("goal"|"audience"), reason, candidates (2–4 concrete options).
- status="ok" if audit is possible (including on inferred). status="needs_clarification" only if goal is completely unverifiable; then auditReport=null.

STEP 1 — goal dimensions (5 items, integer scores 1–5). Anchors:
[hook]        1=first line repels/empty; 3=neutral, not compelling; 5=stakes/benefit/hook clear from line one.
[clarity]     1=unclear what this is and why; 3=readable but scattered/multi-topic; 5=one clear core, easy to retell.
[audienceFit] 1=jargon/level wrong for audience; 3=mostly ok, some misses; 5=language, level, examples fit audience.
[goalService] 1=does not advance goal; 3=partial, gaps remain; 5=directly triggers actions stated in goal.
[cta]         1=no call to action; 3=present but vague or no deadline; 5=one clear CTA: action + deadline.
In rationale — one short phrase in the post's language explaining the score.

STEP 2 — warnings (warnings). Use ONLY codes from the catalog below (LLM judgment only — rule checks run separately on the host).
For each triggered warning: code, severity, source="llm", message (post language), evidence (verbatim excerpt from post ≤12 words; omit if not tied to a fragment).
severity ∈ {info, warning, critical}. Use critical only when the defect blocks the goal; GOAL_ACTION_MISMATCH is always critical.

CATALOG (code — default severity — when to fire):
GOAL_ACTION_MISMATCH   — critical — post does not ask for the action stated in the goal.
BURIED_LEDE            — warning  — main value/motive buried at the end; critical if goal is activating.
GOAL_DRIFT             — warning  — ask is broader/different from declared goal.
WEAK_DELIVERABLE_NAMING— info     — vague ask ("insights", "think about") instead of concrete deliverable.
NO_CLEAR_CTA           — warning  — no explicit CTA or CTA is logistics-only; critical if action is mandatory and absent.
DIFFUSE_ASKS           — warning  — ≥3 different asks in one post, focus blurred.
MIXED_MESSAGES         — warning  — artifact + task + logistics + philosophy mixed together.
EFFORT_ASYMMETRY       — warning  — sloppy/raw post while asking for careful work.
CLICKBAIT              — warning  — promise not backed by content; critical if strongly misleading.
TONE_MISMATCH          — warning  — tone/jargon level mismatches audience.
COGNITIVE_LOAD         — warning  — dense jargon + cross-references, hard to hold in mind.
AI_TELL                — info     — clichés like "in today's fast-changing world".

STEP 3 — goalAlignment assembly (host will recompute overall and cappedBy — still fill them for completeness).
- summary = 1–2 phrases in post language: what works and what pulls down.
- rewriteHints = 3–6 concrete edits in post language.

LANGUAGE: human-readable fields (rationale, message, summary, reason, candidates, rewriteHints, inferred.*) in the post's language. Keys and enums (code, severity, source, key, status, field) in Latin as in schema.

OUTPUT SCHEMA (return exactly one object):
{
  "briefCheck": {
    "status": "ok" | "needs_clarification",
    "inferred": { "goal": string, "audience": string },
    "gaps": [ { "field": "goal"|"audience", "reason": string, "candidates": [string, ...] } ]
  },
  "auditReport": {
    "goalAlignment": {
      "overall": integer,
      "cappedBy": [string, ...],
      "dimensions": [ { "key": "hook"|"clarity"|"audienceFit"|"goalService"|"cta", "score": 1..5, "rationale": string } ],
      "summary": string
    },
    "warnings": [ { "code": string, "severity": "info"|"warning"|"critical", "source": "llm", "message": string, "evidence": string (optional) } ],
    "rewriteHints": [string, ...]
  } | null
}

HARD RULES: JSON only; scores integers 1–5; codes only from catalog; evidence verbatim from post; no extra fields; auditReport=null when status="needs_clarification"."""

FEW_SHOT_USER = """platform: telegram
goal: Register attendees for Thursday 7pm webinar
audience: Product managers who own product metrics
post:
Webinar on product metrics 🚀🚀 Link in bio!!! #product #metrics #growth #pm #webinar #training #analytics"""

FEW_SHOT_ASSISTANT = """{
  "briefCheck": {
    "status": "ok",
    "inferred": { "goal": "Register for product metrics webinar (Thu 7pm)", "audience": "Product managers working with metrics" },
    "gaps": []
  },
  "auditReport": {
    "goalAlignment": {
      "overall": 48,
      "cappedBy": [],
      "dimensions": [
        { "key": "hook", "score": 2, "rationale": "Opens with generic 'webinar on metrics' — no benefit or hook." },
        { "key": "clarity", "score": 3, "rationale": "Topic is clear but when/where/how to register is missing." },
        { "key": "audienceFit", "score": 3, "rationale": "Topic fits PMs but tone is ad-like." },
        { "key": "goalService", "score": 2, "rationale": "Cannot register: no link in post, no date/time." },
        { "key": "cta", "score": 2, "rationale": "'Link in bio' is not an action; no registration form." }
      ],
      "summary": "Topic is clear but the post does not drive registration: no direct link, date, or clear CTA."
    },
    "warnings": [
      { "code": "NO_CLEAR_CTA", "severity": "warning", "source": "llm", "message": "CTA is logistics ('link in bio'), not registration.", "evidence": "Link in bio" },
      { "code": "GOAL_ACTION_MISMATCH", "severity": "critical", "source": "llm", "message": "Goal is registration but post does not enable signing up.", "evidence": "Link in bio" }
    ],
    "rewriteHints": [
      "Put a direct registration link in the post, not 'in bio'.",
      "State date and time (Thursday 7pm) in the text.",
      "Replace ad tone with concrete takeaway: what attendees leave with.",
      "Cut hashtags to 2–3 relevant ones."
    ]
  }
}"""


def build_user_message(platform: str, goal: str, audience: str, post: str) -> str:
    plat = normalize_platform(platform)
    limit = hashtag_limit(platform)
    return f"""platform: {plat}
hashtag_limit: {limit}
goal: {goal}
audience: {audience}
post:
{post}"""


def build_messages(platform: str, goal: str, audience: str, post: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": FEW_SHOT_USER},
        {"role": "assistant", "content": FEW_SHOT_ASSISTANT},
        {"role": "user", "content": build_user_message(platform, goal, audience, post)},
    ]
