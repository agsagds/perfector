"""HTTP client for Modal audit endpoint with mock fallback."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from merge import parse_llm_json
from prompts import FEW_SHOT_ASSISTANT, build_messages


def get_modal_url() -> str | None:
    return os.environ.get("MODAL_AUDIT_URL") or os.environ.get("MODAL_AUDIT_ENDPOINT")


def get_modal_timeout() -> float:
    # Warm latency is ~50s, but a cold container must download + load the ~16 GB
    # model first, which pushes the first request past 2 min. Generous default.
    return float(os.environ.get("MODAL_AUDIT_TIMEOUT", "300"))


def get_ollama_model() -> str | None:
    """Local Ollama model tag (e.g. 'gemma3:4b'); enables the local-LLM path."""
    return os.environ.get("OLLAMA_MODEL")


def get_ollama_url() -> str:
    return os.environ.get("OLLAMA_URL", "http://localhost:11434")


def get_ollama_timeout() -> float:
    # Local CPU/Metal inference is slow: a full audit is ~2.5 min on an M1 with
    # gemma3:4b, and the first (cold) call adds model-load time. Generous default.
    return float(os.environ.get("OLLAMA_TIMEOUT", "300"))


def backend_label() -> str:
    """Human-readable description of the inference backend run() will use."""
    if get_modal_url():
        return "live Gemma 4 E4B on Modal"
    model = get_ollama_model()
    if model:
        return f"local Ollama ({model})"
    return "mock LLM (set MODAL_AUDIT_URL or OLLAMA_MODEL)"


def call_modal_audit(
    platform: str,
    goal: str,
    audience: str,
    post: str,
    *,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Dispatch to a backend: Modal endpoint, local Ollama, or deterministic mock."""
    if timeout is None:
        timeout = get_modal_timeout()
    url = get_modal_url()
    if not url:
        if get_ollama_model():
            return _call_ollama(platform, goal, audience, post)
        return _mock_llm_response(platform, goal, audience, post)

    payload = json.dumps(
        {
            "platform": platform,
            "goal": goal,
            "audience": audience,
            "post": post,
        }
    ).encode("utf-8")
    # Modal serves a single fastapi_endpoint at the root of its URL — no path suffix.
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("MODAL_AUDIT_TOKEN")
    if token:
        headers["X-Audit-Token"] = token
    req = urllib.request.Request(
        url.rstrip("/"),
        data=payload,
        headers=headers,
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


def _ollama_chat(model: str, messages: list[dict[str, str]], timeout: float) -> str:
    """POST messages to Ollama's /api/chat with JSON-constrained output; return content."""
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": False,
            "format": "json",  # constrain output to valid JSON
            "options": {"temperature": 0, "num_predict": 2048},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        get_ollama_url().rstrip("/") + "/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {get_ollama_url()} — is it running? ({exc.reason})"
        ) from exc
    return data.get("message", {}).get("content", "")


def _call_ollama(
    platform: str,
    goal: str,
    audience: str,
    post: str,
    *,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Run the audit against a local Ollama model. First call may be slow (model load)."""
    if timeout is None:
        timeout = get_ollama_timeout()
    model = get_ollama_model()
    messages = build_messages(platform, goal, audience, post)
    raw = _ollama_chat(model, messages, timeout)
    try:
        return parse_llm_json(raw)
    except (json.JSONDecodeError, ValueError):
        # One retry with an explicit instruction, mirroring the Modal path.
        retry = messages + [
            {"role": "user", "content": "Return ONLY valid JSON matching the schema. No other text."}
        ]
        return parse_llm_json(_ollama_chat(model, retry, timeout))


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
