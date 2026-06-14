"""Modal inference service — Gemma 4 E4B post audit, served via Ollama.

Production runner uses Ollama (llama.cpp / quantized GGUF) rather than
transformers: transformers in fp/bf16 is a research/experiment runner, far too
slow and memory-hungry for serving. llama.cpp runs the same gemma4:e4b weights
quantized, which is what the local dev path already uses — so dev and prod share
one stack and one model. The pulled model is cached in a Modal Volume so cold
starts don't re-download the weights.
"""

from __future__ import annotations

import hmac
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import modal

try:  # fastapi is only guaranteed inside the Modal image
    from fastapi import Header, HTTPException
except ModuleNotFoundError:  # deploy-time stub so the module imports locally

    def Header(default=None, **_kwargs):
        return default

    HTTPException = Exception

# Allow importing prompts/merge from the sibling space/ directory.
SPACE_DIR = Path(__file__).resolve().parents[1] / "space"

MODEL = "gemma4:e4b"  # same target model as local dev; quantized GGUF via Ollama
GPU = "L4"
OLLAMA_URL = "http://127.0.0.1:11434"

def _bake_model() -> str:
    # Pull the GGUF at image-build time so it's baked into the layer — cold
    # starts then just load it from local disk instead of downloading ~10 GB
    # under the endpoint's response window.
    return (
        "bash -c 'ollama serve & "
        "for i in $(seq 1 30); do curl -sf http://127.0.0.1:11434/api/tags >/dev/null && break; sleep 1; done; "
        f"ollama pull {MODEL}'"
    )


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("curl", "zstd")  # zstd: required by the Ollama install script
    .run_commands("curl -fsSL https://ollama.com/install.sh | sh")
    .run_commands(_bake_model())
    .pip_install("fastapi[standard]>=0.115.0")
    .add_local_dir(str(SPACE_DIR), remote_path="/root/space")
)

app = modal.App("post-audit-inference", image=image)


@app.cls(
    gpu=GPU,
    timeout=600,
    scaledown_window=300,
)
class AuditModel:
    @modal.enter()
    def start(self):
        sys.path.insert(0, "/root/space")
        # Start the Ollama server (uses the GPU automatically when present).
        # The model is already baked into the image; KEEP_ALIVE=-1 keeps it
        # resident between requests so we pay the GPU load once, not per call.
        self._server = subprocess.Popen(
            ["ollama", "serve"],
            env={**os.environ, "OLLAMA_HOST": "127.0.0.1:11434", "OLLAMA_KEEP_ALIVE": "-1"},
        )
        for _ in range(120):  # serve is usually ready in a few seconds
            try:
                urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3)
                break
            except Exception:  # noqa: BLE001 — connection refused / socket timeout while booting
                time.sleep(1)
        else:
            raise RuntimeError("Ollama server did not become ready in time")
        # Warm the model into the GPU now so the first real request is fast.
        subprocess.run(["ollama", "run", MODEL, "ok"], check=False, timeout=240)
        # Fail fast on silent CPU fallback: if Ollama's GPU libs don't line up
        # with Modal's driver it would run on CPU while still billing the L4.
        # `ollama ps` reports the processor the model actually loaded on.
        ps = subprocess.run(["ollama", "ps"], capture_output=True, text=True)
        print(f"[startup] ollama ps:\n{ps.stdout}", flush=True)
        if "GPU" not in ps.stdout:
            raise RuntimeError(f"Ollama is not using the GPU (ollama ps):\n{ps.stdout}")

    def _chat(self, messages: list[dict[str, str]]) -> str:
        body = json.dumps(
            {
                "model": MODEL,
                "messages": messages,
                "stream": False,
                "format": "json",  # constrain output to valid JSON
                "options": {"temperature": 0, "num_predict": 2048},
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8")).get("message", {}).get("content", "")

    @modal.method()
    def audit(self, platform: str, goal: str, audience: str, post: str) -> dict[str, Any]:
        sys.path.insert(0, "/root/space")
        from merge import parse_llm_json
        from prompts import build_messages

        messages = build_messages(platform, goal, audience, post)
        try:
            return parse_llm_json(self._chat(messages))
        except (json.JSONDecodeError, ValueError):
            retry = messages + [
                {"role": "user", "content": "Return ONLY valid JSON matching the schema. No other text."}
            ]
            return parse_llm_json(self._chat(retry))


# Optional shared secret: export AUDIT_TOKEN before `modal deploy` to require
# an X-Audit-Token header on every request; leave unset to keep the endpoint open.
@app.function(secrets=[modal.Secret.from_dict({"AUDIT_TOKEN": os.environ.get("AUDIT_TOKEN", "")})])
@modal.fastapi_endpoint(method="POST")
def audit_endpoint(body: dict[str, Any], x_audit_token: str | None = Header(default=None)):
    expected = os.environ.get("AUDIT_TOKEN", "")
    if expected and not hmac.compare_digest(x_audit_token or "", expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Audit-Token header")
    platform = body.get("platform", "other")
    goal = body.get("goal", "")
    audience = body.get("audience", "")
    post = body.get("post", "")
    return AuditModel().audit.remote(platform, goal, audience, post)
