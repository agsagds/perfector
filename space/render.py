"""Render audit JSON as HTML for Gradio.

Design: a pre-publish readiness check, not a magazine. Cool grayscale instrument
panel where the only saturated colour is the verdict itself (severity = meaning).
Signature element: a linear readiness meter whose score can be visibly capped by
a blocking finding.
"""

from __future__ import annotations

import html
import json
from typing import Any

DIM_LABELS = {
    "hook": "Hook",
    "clarity": "Clarity",
    "audienceFit": "Audience fit",
    "goalService": "Goal service",
    "cta": "Call to action",
}

SEV_ORDER = {"critical": 0, "warning": 1, "info": 2}
SEV_CLASS = {"critical": "crit", "warning": "warn", "info": "info"}
SEV_LABEL = {"critical": "blocker", "warning": "warning", "info": "note"}


def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""))


def _band(pct: int) -> str:
    if pct < 40:
        return "crit"
    if pct < 70:
        return "warn"
    return "ok"


def _dim_band(score: int) -> str:
    if score <= 2:
        return "crit"
    if score == 3:
        return "warn"
    return "ok"


def _verdict(overall: int, capped: bool) -> tuple[str, str]:
    """Return (headline state, band) — the human verdict that opens the report."""
    if capped:
        return "Not ready to publish", "crit"
    if overall < 40:
        return "Not ready to publish", "crit"
    if overall < 70:
        return "Needs work", "warn"
    return "Ready to publish", "ok"


def _meter(pct: int, capped: bool) -> str:
    pct = max(0, min(100, pct))
    band = _band(pct)
    ceiling = (
        '<div class="m-ceiling" style="left:40%"></div>'
        '<div class="m-ceil-lbl" style="left:40%">ceiling</div>'
        if capped
        else ""
    )
    return f"""<div class="meter">
      <div class="m-track">
        <div class="m-fill {band}" style="width:{pct}%"></div>
        {ceiling}
        <div class="m-tick" style="left:40%"></div>
        <div class="m-tick" style="left:70%"></div>
      </div>
      <div class="m-scale"><span style="left:0">0</span><span style="left:40%">40</span><span style="left:70%">70</span><span style="left:100%">100</span></div>
    </div>"""


def _render_audit(data: dict[str, Any]) -> str:
    ga = data.get("goalAlignment") or {}
    dims = ga.get("dimensions") or []
    overall = int(ga.get("overall") or 0)
    capped_list = ga.get("cappedBy") or []
    capped = bool(capped_list)
    state, band = _verdict(overall, capped)

    warns = sorted(
        data.get("warnings") or [],
        key=lambda w: SEV_ORDER.get(w.get("severity", "info"), 9),
    )
    counts: dict[str, int] = {}
    for w in warns:
        sev = w.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1
    count_str = " · ".join(
        f"{counts[s]} {SEV_LABEL[s]}{'s' if counts[s] > 1 else ''}"
        for s in ("critical", "warning", "info")
        if counts.get(s)
    )

    # Hero — the verdict, the meter, and (the signature) the cap indictment.
    cap_row = ""
    if capped:
        codes = "".join(f'<span class="mono code">{_esc(c)}</span>' for c in capped_list)
        cap_row = (
            f'<div class="cap"><span class="cap-k mono">held at {overall} / 100</span>'
            f'<span class="cap-by">blocked by</span>{codes}</div>'
        )
    summary = _esc(ga.get("summary") or "")
    hero = f"""<header class="hero {band}">
      <div class="eyebrow mono">pre-publish readiness check</div>
      <div class="verdict-row">
        <h1 class="state">{_esc(state)}</h1>
        <div class="score"><b>{overall}</b><span class="mono">/100</span></div>
      </div>
      {_meter(overall, capped)}
      {cap_row}
      {f'<p class="summary">{summary}</p>' if summary else ''}
    </header>"""

    parts = [hero]

    if dims:
        parts.append('<section class="sec"><h2 class="sec-h"><span>Goal dimensions</span>'
                     '<span class="sec-meta mono">score / 5</span></h2><div class="dims">')
        for dm in dims:
            s = int(dm.get("score") or 0)
            dband = _dim_band(s)
            key = dm.get("key", "")
            parts.append(
                f"""<div class="dim">
          <div class="dim-name">{_esc(DIM_LABELS.get(key, key))}<span class="dim-k mono">{_esc(key)}</span></div>
          <div class="dim-body">
            <div class="dim-bar"><div class="dim-track"><div class="dim-fill {dband}" style="width:{(s / 5) * 100}%"></div></div>
            <div class="dim-sc mono">{s}<span>/5</span></div></div>
            <div class="dim-rat">{_esc(dm.get("rationale") or "")}</div>
          </div></div>"""
            )
        parts.append("</div></section>")

    if warns:
        parts.append(
            f'<section class="sec"><h2 class="sec-h"><span>Findings</span>'
            f'<span class="sec-meta mono">{_esc(count_str)}</span></h2><div class="finds">'
        )
        for w in warns:
            cl = SEV_CLASS.get(w.get("severity", "info"), "info")
            label = SEV_LABEL.get(w.get("severity", "info"), "note")
            src = f'<span class="src mono">{_esc(w.get("source"))}</span>' if w.get("source") else ""
            ev = (
                f'<div class="ev mono">{_esc(w.get("evidence"))}</div>'
                if w.get("evidence")
                else ""
            )
            parts.append(
                f"""<div class="find {cl}">
          <div class="find-row">
            <span class="sev {cl} mono">{_esc(label)}</span>
            <span class="code mono">{_esc(w.get("code"))}</span>
            {src}
          </div>
          <div class="find-msg">{_esc(w.get("message"))}</div>
          {ev}
        </div>"""
            )
        parts.append("</div></section>")

    hints = data.get("rewriteHints") or []
    if hints:
        items = "".join(f"<li>{_esc(h)}</li>" for h in hints)
        parts.append(
            f'<section class="sec"><h2 class="sec-h"><span>Fix before publishing</span></h2>'
            f'<ol class="fixes">{items}</ol></section>'
        )

    return "".join(parts)


def _render_brief(data: dict[str, Any]) -> str:
    ok = data.get("status") == "ok"
    state = "Brief accepted" if ok else "Needs a clearer goal"
    band = "ok" if ok else "warn"
    note = (
        "The audit ran on the goal and audience inferred below."
        if ok
        else "The goal is too vague to judge the post against. Pick a concrete target, then re-run."
    )
    inferred = data.get("inferred") or {}
    parts = [
        f"""<header class="hero {band}">
      <div class="eyebrow mono">pre-publish readiness check</div>
      <h1 class="state">{_esc(state)}</h1>
      <p class="summary">{_esc(note)}</p>
    </header>
    <section class="sec"><div class="cards2">
      <div class="infcard"><div class="infcard-t mono">goal · inferred</div><div class="infcard-v">{_esc(inferred.get("goal") or "—")}</div></div>
      <div class="infcard"><div class="infcard-t mono">audience · inferred</div><div class="infcard-v">{_esc(inferred.get("audience") or "—")}</div></div>
    </div></section>"""
    ]
    gaps = data.get("gaps") or []
    if gaps:
        parts.append('<section class="sec"><h2 class="sec-h"><span>What to clarify</span></h2>')
        for g in gaps:
            chips = "".join(f'<span class="chip">{_esc(c)}</span>' for c in g.get("candidates") or [])
            parts.append(
                f"""<div class="gap">
          <span class="fld mono">{_esc(g.get("field"))}</span>
          <div class="gap-reason">{_esc(g.get("reason") or "")}</div>
          <div class="chips">{chips}</div>
        </div>"""
            )
        parts.append("</section>")
    return "".join(parts)


REPORT_CSS = """
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&family=Space+Grotesk:wght@500;700&display=swap');
  .post-audit-report{
    --bg:#eef1f5; --surface:#ffffff; --ink:#161b22; --muted:#586172; --faint:#8a93a3;
    --line:#e3e7ee; --line2:#cfd6e0;
    --ok:#0e7a4f; --ok-bg:#e7f5ee; --ok-line:#c2e4d2;
    --warn:#8a5a00; --warn-bg:#fbefcf; --warn-line:#eedba0;
    --crit:#c12626; --crit-bg:#fcebe9; --crit-line:#f2cbc7;
    --info:#1f5fae; --info-bg:#e9f0fb; --info-line:#cbdcf3;
    --sans:"IBM Plex Sans",system-ui,-apple-system,sans-serif;
    --display:"Space Grotesk",var(--sans); --mono:"IBM Plex Mono",ui-monospace,monospace;
    background:var(--bg); color:var(--ink); font-family:var(--sans);
    font-size:16px; line-height:1.6; border:1px solid var(--line2);
    border-radius:16px; padding:6px; -webkit-font-smoothing:antialiased;
  }
  .post-audit-report *{box-sizing:border-box}
  .post-audit-report .mono{font-family:var(--mono);font-feature-settings:"tnum" 1}
  .post-audit-report h1,.post-audit-report h2{margin:0}

  .post-audit-report .hero{background:var(--surface);border:1px solid var(--line);
    border-radius:13px;padding:22px 22px 20px;position:relative;overflow:hidden}
  .post-audit-report .hero::before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px}
  .post-audit-report .hero.ok::before{background:var(--ok)}
  .post-audit-report .hero.warn::before{background:var(--warn)}
  .post-audit-report .hero.crit::before{background:var(--crit)}
  .post-audit-report .eyebrow{font-size:11px;letter-spacing:.24em;text-transform:uppercase;color:var(--faint)}
  .post-audit-report .verdict-row{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin:8px 0 4px}
  .post-audit-report .state{font-family:var(--display);font-weight:700;font-size:27px;line-height:1.08;letter-spacing:-.01em}
  .post-audit-report .hero.ok .state{color:var(--ok)}
  .post-audit-report .hero.warn .state{color:var(--warn)}
  .post-audit-report .hero.crit .state{color:var(--crit)}
  .post-audit-report .score{font-family:var(--display);display:flex;align-items:baseline;gap:3px;flex:none}
  .post-audit-report .score b{font-size:46px;font-weight:700;line-height:.9;letter-spacing:-.02em}
  .post-audit-report .score span{font-size:13px;color:var(--faint)}
  .post-audit-report .hero.ok .score b{color:var(--ok)}
  .post-audit-report .hero.warn .score b{color:var(--warn)}
  .post-audit-report .hero.crit .score b{color:var(--crit)}

  .post-audit-report .meter{margin:14px 0 2px}
  .post-audit-report .m-track{position:relative;height:10px;border-radius:6px;background:#e6eaf0}
  .post-audit-report .m-fill{position:absolute;left:0;top:0;height:100%;border-radius:6px;
    animation:pa-grow .5s cubic-bezier(.2,.7,.2,1) both}
  .post-audit-report .m-fill.ok{background:var(--ok)}
  .post-audit-report .m-fill.warn{background:var(--warn)}
  .post-audit-report .m-fill.crit{background:var(--crit)}
  .post-audit-report .m-ceiling{position:absolute;top:0;right:0;height:100%;border-radius:0 6px 6px 0;
    background:repeating-linear-gradient(45deg,transparent,transparent 4px,rgba(193,38,38,.16) 4px,rgba(193,38,38,.16) 7px);
    border-left:1.5px dashed var(--crit-line)}
  .post-audit-report .m-ceil-lbl{position:absolute;top:-17px;transform:translateX(4px);font-family:var(--mono);
    font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--crit)}
  .post-audit-report .m-tick{position:absolute;top:-3px;width:1.5px;height:16px;background:var(--line2);transform:translateX(-50%)}
  .post-audit-report .m-scale{position:relative;height:14px;margin-top:7px}
  .post-audit-report .m-scale span{position:absolute;transform:translateX(-50%);font-family:var(--mono);font-size:10px;color:var(--faint)}
  .post-audit-report .m-scale span:first-child{transform:none}
  .post-audit-report .m-scale span:last-child{transform:translateX(-100%)}

  .post-audit-report .cap{display:flex;flex-wrap:wrap;align-items:center;gap:7px;margin-top:14px;
    background:var(--crit-bg);border:1px solid var(--crit-line);border-radius:9px;padding:9px 12px}
  .post-audit-report .cap-k{font-size:11px;color:var(--crit);letter-spacing:.02em}
  .post-audit-report .cap-by{font-size:12px;color:var(--muted)}
  .post-audit-report .summary{font-size:16px;line-height:1.55;color:var(--ink);margin:14px 0 0;max-width:60ch}

  .post-audit-report .sec{margin-top:22px}
  .post-audit-report .sec-h{display:flex;justify-content:space-between;align-items:baseline;
    font-family:var(--mono);font-size:11px;font-weight:500;letter-spacing:.18em;text-transform:uppercase;
    color:var(--muted);padding-bottom:9px;border-bottom:1.5px solid var(--ink);margin-bottom:14px}
  .post-audit-report .sec-meta{color:var(--faint);letter-spacing:.04em}

  .post-audit-report .dims{display:flex;flex-direction:column;gap:2px}
  .post-audit-report .dim{display:grid;grid-template-columns:142px 1fr;gap:10px 18px;align-items:start;
    padding:13px 0;border-bottom:1px solid var(--line)}
  .post-audit-report .dim:last-child{border-bottom:none}
  .post-audit-report .dim-name{font-weight:500;font-size:15px}
  .post-audit-report .dim-k{display:block;font-size:10.5px;color:var(--faint);font-weight:400;margin-top:3px;letter-spacing:.02em}
  .post-audit-report .dim-bar{display:flex;align-items:center;gap:11px;margin-bottom:6px}
  .post-audit-report .dim-track{flex:1;height:6px;border-radius:4px;background:#e6eaf0;overflow:hidden}
  .post-audit-report .dim-fill{height:100%;border-radius:4px;animation:pa-grow .5s cubic-bezier(.2,.7,.2,1) both}
  .post-audit-report .dim-fill.ok{background:var(--ok)} .post-audit-report .dim-fill.warn{background:var(--warn)} .post-audit-report .dim-fill.crit{background:var(--crit)}
  .post-audit-report .dim-sc{font-size:13px;color:var(--muted);min-width:34px;text-align:right}
  .post-audit-report .dim-sc span{color:var(--faint)}
  .post-audit-report .dim-rat{font-size:14px;color:var(--muted);line-height:1.5}

  .post-audit-report .finds{display:flex;flex-direction:column;gap:10px}
  .post-audit-report .find{background:var(--surface);border:1px solid var(--line);border-left-width:4px;
    border-radius:10px;padding:13px 15px 14px}
  .post-audit-report .find.crit{border-left-color:var(--crit)}
  .post-audit-report .find.warn{border-left-color:var(--warn)}
  .post-audit-report .find.info{border-left-color:var(--info)}
  .post-audit-report .find-row{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:7px}
  .post-audit-report .sev{font-size:10px;letter-spacing:.1em;text-transform:uppercase;padding:3px 8px;border-radius:5px;font-weight:500}
  .post-audit-report .sev.crit{color:var(--crit);background:var(--crit-bg)}
  .post-audit-report .sev.warn{color:var(--warn);background:var(--warn-bg)}
  .post-audit-report .sev.info{color:var(--info);background:var(--info-bg)}
  .post-audit-report .code{font-size:12.5px;font-weight:500;color:var(--ink)}
  .post-audit-report .src{margin-left:auto;font-size:10px;color:var(--faint);border:1px solid var(--line2);border-radius:20px;padding:2px 9px}
  .post-audit-report .find-msg{font-size:14.5px;line-height:1.5;color:var(--ink)}
  .post-audit-report .ev{margin-top:10px;font-size:12px;color:var(--muted);background:#f1f4f8;border-radius:7px;
    padding:8px 11px;border-left:2px solid var(--line2);white-space:pre-wrap;word-break:break-word}
  .post-audit-report .ev::before{content:"evidence";display:block;font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--faint);margin-bottom:4px}

  .post-audit-report ol.fixes{list-style:none;counter-reset:f;margin:0;padding:0}
  .post-audit-report ol.fixes li{counter-increment:f;position:relative;padding:11px 0 11px 40px;
    border-bottom:1px solid var(--line);font-size:15px;line-height:1.5}
  .post-audit-report ol.fixes li:last-child{border-bottom:none}
  .post-audit-report ol.fixes li::before{content:counter(f,decimal-leading-zero);position:absolute;left:0;top:12px;
    font-family:var(--mono);font-size:12px;color:var(--ink);font-weight:500}

  .post-audit-report .cards2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
  .post-audit-report .infcard{background:var(--surface);border:1px solid var(--line);border-radius:11px;padding:14px 16px}
  .post-audit-report .infcard-t{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint);margin-bottom:7px}
  .post-audit-report .infcard-v{font-size:15px;line-height:1.5}
  .post-audit-report .gap{background:var(--surface);border:1px solid var(--line);border-radius:11px;padding:14px 16px;margin-bottom:11px}
  .post-audit-report .fld{display:inline-block;font-size:11px;background:var(--warn-bg);color:var(--warn);padding:3px 9px;border-radius:5px;margin-bottom:9px}
  .post-audit-report .gap-reason{font-size:14.5px;color:var(--muted);margin-bottom:11px}
  .post-audit-report .chips{display:flex;flex-wrap:wrap;gap:7px}
  .post-audit-report .chip{font-size:13px;border:1px solid var(--line2);border-radius:20px;padding:5px 13px;background:var(--surface)}

  @media(max-width:620px){
    .post-audit-report .cards2{grid-template-columns:1fr}
    .post-audit-report .dim{grid-template-columns:1fr}
    .post-audit-report .score b{font-size:38px}
    .post-audit-report .state{font-size:23px}
  }
  @keyframes pa-grow{from{width:0 !important}}
  @media(prefers-reduced-motion:reduce){.post-audit-report .m-fill,.post-audit-report .dim-fill{animation:none}}
"""


def render_report_html(payload: dict[str, Any]) -> str:
    """Build full HTML fragment for gr.HTML from merged or viewer payload."""
    if payload.get("goalAlignment"):
        body = _render_audit(payload)
    elif payload.get("status") or payload.get("inferred"):
        body = _render_brief(payload)
    else:
        body = (
            '<header class="hero warn"><div class="eyebrow mono">pre-publish readiness check</div>'
            '<h1 class="state">Unexpected output</h1>'
            f'<p class="summary mono">{_esc(json.dumps(payload)[:200])}</p></header>'
        )
    return f'<div class="post-audit-report"><style>{REPORT_CSS}</style>{body}</div>'
