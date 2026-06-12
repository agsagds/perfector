"""Post Audit — Gradio Space entrypoint."""

from __future__ import annotations

import gradio as gr

from audit_client import call_modal_audit, get_modal_url
from examples import EXAMPLE_CHAT_DUMP, EXAMPLE_WEBINAR
from merge import merge_audit, viewer_payload
from render import render_report_html
from rules import run_rules


def run_audit(platform: str, goal: str, audience: str, post: str):
    if not post.strip():
        return "<p>Enter a post to audit.</p>", {}

    rule_warnings = run_rules(platform, goal, audience, post)
    try:
        llm_payload = call_modal_audit(platform, goal, audience, post)
    except Exception as exc:
        err = f"<p style='color:#b3261e'>Audit failed: {exc}</p>"
        return err, {}

    merged = merge_audit(llm_payload, rule_warnings)
    view = viewer_payload(merged)
    report_html = render_report_html(view)

    mode = "live Gemma 4 E4B on Modal" if get_modal_url() else "mock LLM (set MODAL_AUDIT_URL)"
    status = f"<p><strong>Done.</strong> Inference: {mode}. Rule warnings: {len(rule_warnings)}.</p>"

    return status + report_html, merged


def load_example(example: dict):
    return example["platform"], example["goal"], example["audience"], example["post"]


with gr.Blocks(title="Post Audit", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
# Post Audit
Audit a social post against your **goal** and **audience** before you publish.

Hybrid pipeline: deterministic rule linters + **Gemma 4 E4B** (4.5B effective) on Modal.
First run may take ~30s while the GPU container starts.
"""
    )

    with gr.Row():
        platform = gr.Dropdown(
            choices=["Telegram", "LinkedIn", "X/Twitter", "Other"],
            value="Telegram",
            label="Platform",
        )
    goal = gr.Textbox(label="Goal", placeholder="Register attendees for Thursday 7pm webinar")
    audience = gr.Textbox(
        label="Audience",
        placeholder="Product managers who own product metrics",
    )
    post = gr.Textbox(
        label="Post draft",
        lines=10,
        placeholder="Paste your post here…",
    )

    with gr.Row():
        audit_btn = gr.Button("Run audit", variant="primary")
        ex_webinar = gr.Button("Load example: weak webinar CTA")
        ex_chat = gr.Button("Load example: chat dump")

    with gr.Accordion("Raw JSON", open=False):
        raw_json = gr.JSON(label="Pipeline output")

    audit_btn.click(
        fn=run_audit,
        inputs=[platform, goal, audience, post],
        outputs=[status_report, raw_json],
    )
    ex_webinar.click(
        fn=lambda: load_example(EXAMPLE_WEBINAR),
        outputs=[platform, goal, audience, post],
    )
    ex_chat.click(
        fn=lambda: load_example(EXAMPLE_CHAT_DUMP),
        outputs=[platform, goal, audience, post],
    )

if __name__ == "__main__":
    demo.launch()
