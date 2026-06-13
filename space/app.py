"""Post Audit — Gradio Space entrypoint."""

from __future__ import annotations

import html

import gradio as gr

from audit_client import backend_label, call_modal_audit
from examples import EXAMPLE_CHAT_DUMP, EXAMPLE_WEBINAR
from merge import merge_audit, viewer_payload
from render import render_report_html
from rules import run_rules

# Shared visual language with the report (see render.py :root).
_STATUS_CSS = """
<style>
  .pa-status{font-family:"Golos Text",system-ui,sans-serif;background:#fffdf8;
    border:1px solid #e7e0d2;border-radius:14px;padding:18px 20px;margin:4px 0 2px;
    display:flex;align-items:center;gap:16px;color:#211f1b}
  .pa-status .pa-spinner{flex:none;width:26px;height:26px;border-radius:50%;
    border:3px solid #e7e0d2;border-top-color:#211f1b;animation:pa-spin .9s linear infinite}
  .pa-status .pa-txt{display:flex;flex-direction:column;gap:3px;min-width:0}
  .pa-status .pa-txt strong{font-size:15px}
  .pa-status .pa-txt span{font-size:13px;color:#5c574d;line-height:1.45}
  .pa-status.pa-done{border-left:4px solid #2e7d4f}
  .pa-status.pa-error{border-left:4px solid #b3261e}
  .pa-status .pa-meta{font-family:"JetBrains Mono",monospace;font-size:11px;
    letter-spacing:.04em;color:#928c7e}
  .pa-bar{position:relative;height:4px;border-radius:4px;background:#ece5d6;
    overflow:hidden;margin-top:14px}
  .pa-bar > span{position:absolute;top:0;left:0;height:100%;width:40%;border-radius:4px;
    background:#211f1b;animation:pa-slide 1.25s ease-in-out infinite}
  @keyframes pa-spin{to{transform:rotate(360deg)}}
  @keyframes pa-slide{0%{left:-40%}50%{left:60%}100%{left:110%}}
</style>
"""

_LOADING_HTML = _STATUS_CSS + """
<div class="pa-status">
  <div class="pa-spinner" aria-hidden="true"></div>
  <div class="pa-txt">
    <strong>Analyzing your post…</strong>
    <span>Running rule linters and <b>Gemma&nbsp;4&nbsp;E4B</b> on GPU. A cold start can take
    up to ~2&nbsp;minutes while the model loads — this is normal, no need to click again.</span>
  </div>
</div>
<div class="pa-bar"><span></span></div>
"""


def _empty_html() -> str:
    return _STATUS_CSS + (
        '<div class="pa-status pa-error"><div class="pa-txt">'
        "<strong>Nothing to audit</strong><span>Enter a post draft above, then run the audit.</span>"
        "</div></div>"
    )


def _error_html(exc: Exception) -> str:
    return _STATUS_CSS + (
        '<div class="pa-status pa-error"><div class="pa-txt">'
        "<strong>Audit failed</strong>"
        f"<span>{html.escape(str(exc))}</span>"
        "</div></div>"
    )


def _done_status(rule_count: int) -> str:
    return _STATUS_CSS + (
        '<div class="pa-status pa-done"><div class="pa-txt">'
        "<strong>Audit complete</strong>"
        f'<span class="pa-meta">Inference: {backend_label()} · rule warnings: {rule_count}</span>'
        "</div></div>"
    )


def run_audit(platform: str, goal: str, audience: str, post: str):
    """Generator: emit an immediate loading state, then the rendered report.

    Yields (status_report_html, raw_json, button_update) so the UI updates the
    instant the user clicks — instead of looking frozen during the long GPU call.
    """
    btn_busy = gr.update(value="Analyzing…", interactive=False)
    btn_idle = gr.update(value="Run audit", interactive=True)

    if not post.strip():
        yield _empty_html(), {}, btn_idle
        return

    # Instant feedback + lock the button against repeat clicks.
    yield _LOADING_HTML, {}, btn_busy

    rule_warnings = run_rules(platform, goal, audience, post)
    try:
        llm_payload = call_modal_audit(platform, goal, audience, post)
    except Exception as exc:  # noqa: BLE001 — surface any backend failure to the user
        yield _error_html(exc), {}, btn_idle
        return

    merged = merge_audit(llm_payload, rule_warnings)
    report_html = render_report_html(viewer_payload(merged))

    yield _done_status(len(rule_warnings)) + report_html, merged, btn_idle


def load_example(example: dict):
    return example["platform"], example["goal"], example["audience"], example["post"]


with gr.Blocks(title="Post Audit", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
# Post Audit
Audit a social post against your **goal** and **audience** before you publish.

Hybrid pipeline: deterministic rule linters + **Gemma 4 E4B** (4.5B effective) on Modal.
The first run after the app has been idle can take up to ~2 minutes while the GPU container
loads the model; later runs are much faster.
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

    status_report = gr.HTML()

    with gr.Accordion("Raw JSON", open=False):
        raw_json = gr.JSON(label="Pipeline output")

    audit_btn.click(
        fn=run_audit,
        inputs=[platform, goal, audience, post],
        outputs=[status_report, raw_json, audit_btn],
        show_progress="hidden",  # our own loading card is the progress indicator
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
