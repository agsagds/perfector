"""Modal inference service — Gemma 4 E4B post audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import modal

# Allow importing prompts from sibling space/ directory
SPACE_DIR = Path(__file__).resolve().parents[1] / "space"

MODEL_ID = "google/gemma-4-E4B-it"
GPU = "L4"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.4.0",
        "transformers>=4.51.0",
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
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        sys.path.insert(0, "/root/space")
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
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


@app.function()
@modal.fastapi_endpoint(method="POST")
def audit_endpoint(body: dict[str, Any]):
    platform = body.get("platform", "other")
    goal = body.get("goal", "")
    audience = body.get("audience", "")
    post = body.get("post", "")
    return AuditModel().audit.remote(platform, goal, audience, post)
