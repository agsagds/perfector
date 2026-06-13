"""Modal inference service — Gemma 4 E4B post audit."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import modal

try:  # fastapi is only guaranteed inside the Modal image
    from fastapi import Header, HTTPException
except ModuleNotFoundError:  # deploy-time stub so the module imports locally

    def Header(default=None, **_kwargs):
        return default

    HTTPException = Exception

# Allow importing prompts from sibling space/ directory
SPACE_DIR = Path(__file__).resolve().parents[1] / "space"

MODEL_ID = "google/gemma-4-E4B-it"
GPU = "L4"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.4.0",
        # gemma4 support; the model's config.json is written by transformers 5.5.0.dev0
        "transformers>=5.5.0",
        "accelerate>=1.0.0",
        "huggingface_hub>=0.27.0",
        "sentencepiece>=0.2.0",
        "fastapi[standard]>=0.115.0",
    )
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
    def load(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        sys.path.insert(0, "/root/space")
        # Text-only audit: AutoTokenizer, not AutoProcessor. Gemma 4 is multimodal,
        # so AutoProcessor (Gemma4Processor) requires image backends (PIL/torchvision)
        # we don't need and don't ship. The tokenizer carries the same chat template.
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            dtype="auto",
            device_map="auto",
        )
        self.model.eval()

    def _generate(self, messages: list[dict[str, str]], retry_suffix: str | None = None) -> str:
        import torch

        if retry_suffix:
            messages = messages + [{"role": "user", "content": retry_suffix}]

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,  # we need raw JSON, not reasoning traces
        )
        prompt += "{"

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=2048,
                do_sample=False,
                temperature=None,
                top_p=None,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        text = self.tokenizer.decode(out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
        return "{" + text.strip()

    @modal.method()
    def audit(
        self,
        platform: str,
        goal: str,
        audience: str,
        post: str,
    ) -> dict[str, Any]:
        sys.path.insert(0, "/root/space")
        from merge import parse_llm_json
        from prompts import build_messages

        messages = build_messages(platform, goal, audience, post)
        raw = self._generate(messages)
        try:
            return parse_llm_json(raw)
        except (json.JSONDecodeError, ValueError):
            raw = self._generate(
                messages,
                retry_suffix="Return ONLY valid JSON matching the schema. No other text.",
            )
            return parse_llm_json(raw)


# Optional shared secret: export AUDIT_TOKEN before `modal deploy` to require
# an X-Audit-Token header on every request; leave unset to keep the endpoint open.
@app.function(secrets=[modal.Secret.from_dict({"AUDIT_TOKEN": os.environ.get("AUDIT_TOKEN", "")})])
@modal.fastapi_endpoint(method="POST")
def audit_endpoint(body: dict[str, Any], x_audit_token: str | None = Header(default=None)):
    expected = os.environ.get("AUDIT_TOKEN", "")
    if expected and x_audit_token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Audit-Token header")
    platform = body.get("platform", "other")
    goal = body.get("goal", "")
    audience = body.get("audience", "")
    post = body.get("post", "")
    return AuditModel().audit.remote(platform, goal, audience, post)
