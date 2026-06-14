"""Post Audit — Gradio Space entrypoint."""

from __future__ import annotations

import html

import gradio as gr

from audit_client import backend_label, call_modal_audit
from examples import EXAMPLE_CHAT_DUMP, EXAMPLE_WEBINAR
from merge import merge_audit, viewer_payload
from render import render_report_html
from rules import run_rules

# Shared visual language with the report (see render.py :root): cool slate,
# Space Grotesk for the verdict word, IBM Plex Mono for meta.
_STATUS_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&family=Space+Grotesk:wght@500;700&display=swap');
  .pa-status{font-family:"IBM Plex Sans",system-ui,sans-serif;background:#ffffff;
    border:1px solid #e3e7ee;border-radius:13px;padding:18px 20px;margin:4px 0 2px;
    display:flex;align-items:center;gap:16px;color:#161b22;color-scheme:light}
  .pa-status .pa-spinner{flex:none;width:26px;height:26px;border-radius:50%;
    border:3px solid #e6eaf0;border-top-color:#161b22;animation:pa-spin .9s linear infinite}
  .pa-status .pa-txt{display:flex;flex-direction:column;gap:3px;min-width:0}
  .pa-status .pa-txt strong{font-family:"Space Grotesk","IBM Plex Sans",sans-serif;font-size:16px;font-weight:700;letter-spacing:-.01em;color:#161b22}
  .pa-status .pa-txt span{font-size:13px;color:#586172;line-height:1.45}
  .pa-status.pa-done{border-left:4px solid #0e7a4f}
  .pa-status.pa-done .pa-txt strong{color:#0e7a4f}
  .pa-status.pa-error{border-left:4px solid #c12626}
  .pa-status.pa-error .pa-txt strong{color:#c12626}
  .pa-status .pa-meta{font-family:"IBM Plex Mono",monospace;font-size:11px;
    letter-spacing:.04em;color:#8a93a3}
  .pa-bar{position:relative;height:4px;border-radius:4px;background:#e6eaf0;
    overflow:hidden;margin-top:14px}
  .pa-bar > span{position:absolute;top:0;left:0;height:100%;width:40%;border-radius:4px;
    background:#161b22;animation:pa-slide 1.25s ease-in-out infinite}
  @keyframes pa-spin{to{transform:rotate(360deg)}}
  @keyframes pa-slide{0%{left:-40%}50%{left:60%}100%{left:110%}}
  @media(prefers-reduced-motion:reduce){.pa-status .pa-spinner{animation:none}.pa-bar > span{animation:none;width:100%;opacity:.4}}
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


# Dark mode in Gradio is just a `dark` class on <body> (the served bundle does
# `document.body.classList.add("dark")`); toggling it flips every theme CSS var to
# its `_dark` variant. The report/status cards pin their own light colors
# (color-scheme:light) on purpose, so they stay legible either way.
_THEME_TOGGLE_JS = """
() => {
  const dark = document.body.classList.toggle('dark');
  const b = document.getElementById('pa-theme-toggle');
  if (b) b.textContent = dark ? '☀ Light mode' : '☾ Dark mode';
}
"""

# Label the button for the *current* state on load — the app may already be dark
# (system preference or ?__theme=dark) before the user ever clicks.
_THEME_INIT_JS = """
() => {
  const b = document.getElementById('pa-theme-toggle');
  if (b) b.textContent = document.body.classList.contains('dark') ? '☀ Light mode' : '☾ Dark mode';
}
"""


# Page identity matches the report (render.py): cool slate instrument panel,
# Space Grotesk display, IBM Plex Sans body, IBM Plex Mono labels/codes.
_THEME = gr.themes.Base(
    primary_hue=gr.themes.colors.slate,
    neutral_hue=gr.themes.colors.slate,
    font=[gr.themes.GoogleFont("IBM Plex Sans"), "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "ui-monospace", "monospace"],
).set(
    body_background_fill="#eef1f5",
    body_text_color="#161b22",
    block_background_fill="#ffffff",
    block_border_color="#e3e7ee",
    block_label_text_color="#586172",
    block_title_text_color="#161b22",
    input_background_fill="#ffffff",
    input_border_color="#cfd6e0",
    input_border_color_focus="#161b22",
    button_large_radius="10px",
    button_primary_background_fill="#161b22",
    button_primary_background_fill_hover="#2a313c",
    button_primary_text_color="#ffffff",
    button_primary_border_color="#161b22",
    button_secondary_background_fill="#ffffff",
    button_secondary_background_fill_hover="#f1f4f8",
    button_secondary_border_color="#cfd6e0",
    button_secondary_text_color="#161b22",
)

_PAGE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&family=Space+Grotesk:wght@500;700&display=swap');
.gradio-container{background:#eef1f5}
.pa-head{padding:6px 2px 4px}
.pa-head .eyebrow{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.24em;
  text-transform:uppercase;color:#8a93a3}
.pa-head h1{font-family:"Space Grotesk","IBM Plex Sans",sans-serif;font-weight:700;font-size:30px;
  letter-spacing:-.015em;color:#161b22;margin:7px 0 0}
.pa-head .sub{font-family:"IBM Plex Sans",sans-serif;font-size:15px;color:#586172;line-height:1.5;margin:9px 0 0;max-width:62ch}
.pa-head .note{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:#8a93a3;margin:9px 0 0}
.pa-head .rule{height:1.5px;background:#161b22;margin:16px 0 2px}
/* component labels as quiet mono captions, echoing the report's section heads */
.gradio-container .block .label-wrap > span,
.gradio-container label[data-testid] > span:first-child,
.gradio-container span[data-testid="block-info"]{font-family:"IBM Plex Mono",monospace;
  font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#586172}
.gradio-container .primary{font-weight:500}
"""

_HEADER_HTML = """
<div class="pa-head">
  <div class="eyebrow">pre-publish readiness check</div>
  <h1>Post Audit</h1>
  <p class="sub">Check a draft against your stated goal and audience before you publish —
  deterministic rule linters plus Gemma 4 E4B on Modal.</p>
  <p class="note">First run after idle can take up to ~2 min while the GPU loads the model; later runs are faster.</p>
  <div class="rule"></div>
</div>
"""


# theme/css are set in BOTH places on purpose (Gradio 6). Whichever code path
# serves the app, the theme survives:
#   - run as __main__ (`python app.py`, HF Spaces): the explicit launch() args win.
#   - imported & launched by another runner with no args (the `gradio` CLI reload
#     runner, and possibly HF's launcher): the constructor args are re-applied at
#     launch() time via Gradio's `_deprecated_theme`/`_deprecated_css` shim.
# The constructor form emits a (benign) deprecation warning; that is the price of
# covering the import-and-launch path. See tests/test_app_theme.py.
with gr.Blocks(title="Post Audit", theme=_THEME, css=_PAGE_CSS) as demo:
    gr.HTML(_HEADER_HTML)

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
        theme_btn = gr.Button("☾ Dark mode", elem_id="pa-theme-toggle", scale=0)

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
    theme_btn.click(fn=None, inputs=None, outputs=None, js=_THEME_TOGGLE_JS)

    demo.load(fn=None, inputs=None, outputs=None, js=_THEME_INIT_JS)

if __name__ == "__main__":
    demo.launch(theme=_THEME, css=_PAGE_CSS)
