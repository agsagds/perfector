"""Render audit JSON as HTML for Gradio (ported from post-audit-viewer.html)."""

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


def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""))


def _band_color(pct: int) -> str:
    if pct < 40:
        return "var(--crit)"
    if pct < 70:
        return "var(--warn)"
    return "var(--ok)"


def _dim_color(score: int) -> str:
    if score <= 2:
        return "var(--crit)"
    if score == 3:
        return "var(--warn)"
    return "var(--ok)"


def _gauge(pct: int) -> str:
    r = 60
    c = 2 * 3.14159265 * r
    off = c * (1 - max(0, min(100, pct)) / 100)
    col = _band_color(pct)
    return f"""<div class="gauge">
      <svg width="138" height="138" viewBox="0 0 138 138">
        <circle cx="69" cy="69" r="{r}" fill="none" stroke="#ece6d8" stroke-width="9"/>
        <circle cx="69" cy="69" r="{r}" fill="none" stroke="{col}" stroke-width="9" stroke-linecap="round"
          stroke-dasharray="{c:.1f}" stroke-dashoffset="{off:.1f}" transform="rotate(-90 69 69)"/>
      </svg>
      <div class="num"><b style="color:{col}">{pct}</b><span>of 100</span></div>
    </div>"""


def _render_audit(data: dict[str, Any]) -> str:
    ga = data.get("goalAlignment") or {}
    dims = ga.get("dimensions") or []
    warns = sorted(
        data.get("warnings") or [],
        key=lambda w: SEV_ORDER.get(w.get("severity", "info"), 9),
    )
    counts: dict[str, int] = {}
    for w in warns:
        sev = w.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1
    count_str = " · ".join(f"{counts[s]} {s}" for s in ("critical", "warning", "info") if counts.get(s))

    parts = [
        f"""<section class="sec"><div class="head">
      {_gauge(int(ga.get("overall") or 0))}
      <div class="lead">
        <p class="verdict">{_esc(ga.get("summary") or "")}</p>"""
    ]
    capped = ga.get("cappedBy") or []
    if capped:
        tags = "".join(f'<span class="tag crit mono">{_esc(c)}</span>' for c in capped)
        parts.append(f'<div class="capped"><span class="lbl">capped by:</span>{tags}</div>')
    parts.append("</div></div></section>")

    if dims:
        parts.append(
            '<section class="sec"><div class="sec-h"><span>Goal dimensions</span>'
            '<span class="wcount">score / 5</span></div>'
        )
        for dm in dims:
            s = int(dm.get("score") or 0)
            pct = (s / 5) * 100
            col = _dim_color(s)
            key = dm.get("key", "")
            parts.append(
                f"""<div class="dim">
          <div class="name">{_esc(DIM_LABELS.get(key, key))}<span class="k">{_esc(key)}</span></div>
          <div class="body">
            <div class="bar"><div class="track"><div class="fill" style="width:{pct}%;background:{col}"></div></div>
            <div class="sc">{s}/5</div></div>
            <div class="rat">{_esc(dm.get("rationale") or "")}</div>
          </div></div>"""
            )
        parts.append("</section>")

    if warns:
        parts.append(
            f'<section class="sec"><div class="sec-h"><span>Warnings</span>'
            f'<span class="wcount">{_esc(count_str)}</span></div>'
        )
        for i, w in enumerate(warns):
            cl = SEV_CLASS.get(w.get("severity", "info"), "info")
            src = f'<span class="src">{_esc(w.get("source"))}</span>' if w.get("source") else ""
            ev = (
                f'<div class="ev">{_esc(w.get("evidence"))}</div>'
                if w.get("evidence")
                else ""
            )
            parts.append(
                f"""<div class="w {cl}" style="--i:{i}">
          <div class="row">
            <span class="sev {cl}">{_esc(w.get("severity"))}</span>
            <span class="code">{_esc(w.get("code"))}</span>
            {src}
          </div>
          <div class="msg">{_esc(w.get("message"))}</div>
          {ev}
        </div>"""
            )
        parts.append("</section>")

    hints = data.get("rewriteHints") or []
    if hints:
        items = "".join(f"<li>{_esc(h)}</li>" for h in hints)
        parts.append(
            f'<section class="sec"><div class="sec-h"><span>Rewrite hints</span></div>'
            f'<ol class="hints">{items}</ol></section>'
        )

    return "".join(parts)


def _render_brief(data: dict[str, Any]) -> str:
    ok = data.get("status") == "ok"
    status_cls = "ok" if ok else "clar"
    status_txt = (
        "Brief accepted — audit uses inferred fields"
        if ok
        else "Needs clarification"
    )
    inferred = data.get("inferred") or {}
    parts = [
        f"""<section class="sec">
      <span class="status {status_cls}"><span class="dot"></span>{status_txt}</span>
      <div class="cards2" style="margin-top:16px">
        <div class="infcard"><div class="t">Goal (inferred)</div><div class="v">{_esc(inferred.get("goal") or "—")}</div></div>
        <div class="infcard"><div class="t">Audience (inferred)</div><div class="v">{_esc(inferred.get("audience") or "—")}</div></div>
      </div></section>"""
    ]
    for g in data.get("gaps") or []:
        chips = "".join(f'<span class="chip">{_esc(c)}</span>' for c in g.get("candidates") or [])
        parts.append(
            f"""<section class="sec"><div class="sec-h"><span>Gaps</span></div>
        <div class="gap">
        <span class="fld">{_esc(g.get("field"))}</span>
        <div class="reason">{_esc(g.get("reason") or "")}</div>
        <div class="chips">{chips}</div>
      </div></section>"""
        )
    return "".join(parts)


REPORT_CSS = """
  :root{
    --paper:#f5f1e8; --card:#fffdf8; --ink:#211f1b; --soft:#5c574d; --faint:#928c7e;
    --rule:#e2dccd; --rule-2:#d3ccb8;
    --crit:#b3261e; --crit-bg:#fbe9e6; --warn:#956000; --warn-bg:#faf0d6; --info:#2b5f8a; --info-bg:#e6eef6;
    --ok:#2f6b34; --ok-bg:#e8f1e3;
  }
  .post-audit-report *{box-sizing:border-box}
  .post-audit-report{
    background:var(--paper); color:var(--ink);
    font-family:"Golos Text",system-ui,sans-serif; font-size:16px; line-height:1.6;
    border:1px solid var(--rule); border-radius:14px; padding:24px 20px;
  }
  .post-audit-report .mono{font-family:"JetBrains Mono",monospace}
  .post-audit-report header.top{border-bottom:2px solid var(--ink);padding-bottom:14px;margin-bottom:20px}
  .post-audit-report header.top .kicker{font-family:"JetBrains Mono",monospace;font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--faint)}
  .post-audit-report header.top h1{font-family:Georgia,serif;font-weight:700;font-size:28px;line-height:1.1;margin:6px 0 0}
  .post-audit-report .sec{margin-top:28px}
  .post-audit-report .sec-h{font-family:"JetBrains Mono",monospace;font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--faint);
    border-bottom:1px solid var(--rule);padding-bottom:8px;margin-bottom:18px;display:flex;justify-content:space-between;align-items:baseline}
  .post-audit-report .head{display:flex;gap:26px;align-items:center;flex-wrap:wrap}
  .post-audit-report .gauge{flex:0 0 auto;position:relative;width:138px;height:138px}
  .post-audit-report .gauge .num{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
  .post-audit-report .gauge .num b{font-family:Georgia,serif;font-size:42px;font-weight:700;line-height:1}
  .post-audit-report .gauge .num span{font-size:11px;color:var(--faint);font-family:"JetBrains Mono",monospace;margin-top:2px}
  .post-audit-report .head .lead{flex:1 1 280px;min-width:220px}
  .post-audit-report .head .lead .verdict{font-family:Georgia,serif;font-size:20px;line-height:1.32;font-weight:500;margin:0 0 12px}
  .post-audit-report .capped{display:flex;flex-wrap:wrap;gap:6px}
  .post-audit-report .capped .lbl{font-size:11px;color:var(--faint);font-family:"JetBrains Mono",monospace;align-self:center;margin-right:2px}
  .post-audit-report .tag{font-family:"JetBrains Mono",monospace;font-size:11px;padding:3px 8px;border-radius:6px;border:1px solid;letter-spacing:.02em}
  .post-audit-report .tag.crit{color:var(--crit);background:var(--crit-bg);border-color:#eecfca}
  .post-audit-report .dim{display:grid;grid-template-columns:150px 1fr;gap:14px 18px;align-items:start;padding:14px 0;border-bottom:1px solid var(--rule)}
  .post-audit-report .dim:last-child{border-bottom:none}
  .post-audit-report .dim .name{font-weight:600;font-size:15px}
  .post-audit-report .dim .name .k{display:block;font-family:"JetBrains Mono",monospace;font-size:10.5px;color:var(--faint);font-weight:400;margin-top:2px}
  .post-audit-report .dim .body .bar{display:flex;align-items:center;gap:10px;margin-bottom:7px}
  .post-audit-report .track{flex:1;height:7px;border-radius:4px;background:#ece6d8;overflow:hidden}
  .post-audit-report .fill{height:100%;border-radius:4px}
  .post-audit-report .dim .sc{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--soft);min-width:30px;text-align:right}
  .post-audit-report .dim .rat{font-size:14px;color:var(--soft);line-height:1.5}
  .post-audit-report .wcount{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--faint);letter-spacing:.04em}
  .post-audit-report .w{position:relative;background:var(--card);border:1px solid var(--rule);border-left-width:4px;border-radius:10px;padding:13px 16px 15px;margin-bottom:11px}
  .post-audit-report .w.crit{border-left-color:var(--crit)} .post-audit-report .w.warn{border-left-color:var(--warn)} .post-audit-report .w.info{border-left-color:var(--info)}
  .post-audit-report .w .row{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:7px}
  .post-audit-report .sev{font-family:"JetBrains Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;padding:3px 7px;border-radius:5px;font-weight:500}
  .post-audit-report .sev.crit{color:var(--crit);background:var(--crit-bg)} .post-audit-report .sev.warn{color:var(--warn);background:var(--warn-bg)} .post-audit-report .sev.info{color:var(--info);background:var(--info-bg)}
  .post-audit-report .code{font-family:"JetBrains Mono",monospace;font-size:12.5px;font-weight:500}
  .post-audit-report .src{margin-left:auto;font-family:"JetBrains Mono",monospace;font-size:10px;color:var(--faint);border:1px solid var(--rule-2);border-radius:20px;padding:2px 9px}
  .post-audit-report .w .msg{font-size:14.5px;line-height:1.5}
  .post-audit-report .ev{margin-top:10px;font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--soft);background:#f3eee2;border-radius:7px;padding:8px 11px;border-left:2px solid var(--rule-2);white-space:pre-wrap;word-break:break-word}
  .post-audit-report .ev::before{content:"evidence";display:block;font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--faint);margin-bottom:4px}
  .post-audit-report ol.hints{list-style:none;counter-reset:h;margin:0;padding:0}
  .post-audit-report ol.hints li{counter-increment:h;position:relative;padding:11px 0 11px 42px;border-bottom:1px solid var(--rule);font-size:15px;line-height:1.5;color:var(--ink)}
  .post-audit-report ol.hints li:last-child{border-bottom:none}
  .post-audit-report ol.hints li::before{content:counter(h,decimal-leading-zero);position:absolute;left:0;top:11px;font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--faint);font-weight:500}
  .post-audit-report .cards2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  @media(max-width:620px){.post-audit-report .cards2{grid-template-columns:1fr}.post-audit-report .dim{grid-template-columns:1fr}}
  .post-audit-report .infcard{background:var(--card);border:1px solid var(--rule);border-radius:11px;padding:15px 17px}
  .post-audit-report .infcard .t{font-family:"JetBrains Mono",monospace;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);margin-bottom:7px}
  .post-audit-report .infcard .v{font-size:15px;line-height:1.5}
  .post-audit-report .gap{background:var(--card);border:1px solid var(--rule);border-radius:11px;padding:15px 17px;margin-top:13px}
  .post-audit-report .gap .fld{display:inline-block;font-family:"JetBrains Mono",monospace;font-size:11px;background:var(--warn-bg);color:var(--warn);padding:3px 8px;border-radius:5px;margin-bottom:8px}
  .post-audit-report .gap .reason{font-size:14.5px;color:var(--soft);margin-bottom:11px}
  .post-audit-report .chips{display:flex;flex-wrap:wrap;gap:7px}
  .post-audit-report .chip{font-size:13px;border:1px solid var(--rule-2);border-radius:20px;padding:5px 13px;background:#fcfaf4}
  .post-audit-report .status{display:inline-flex;align-items:center;gap:8px;font-family:"JetBrains Mono",monospace;font-size:12px;padding:6px 13px;border-radius:8px;font-weight:500}
  .post-audit-report .status.ok{color:var(--ok);background:var(--ok-bg)} .post-audit-report .status.clar{color:var(--warn);background:var(--warn-bg)}
  .post-audit-report .dot{width:7px;height:7px;border-radius:50%;background:currentColor}
"""


def render_report_html(payload: dict[str, Any]) -> str:
    """Build full HTML fragment for gr.HTML from merged or viewer payload."""
    if payload.get("goalAlignment"):
        body = _render_audit(payload)
        subtitle = "Structured audit against your stated goal and audience."
    elif payload.get("status") or payload.get("inferred"):
        body = _render_brief(payload)
        subtitle = "Brief check — clarify gaps before a full audit."
    else:
        body = f'<p class="rat">Unexpected payload: {_esc(json.dumps(payload)[:200])}</p>'
        subtitle = "Report"

    return f"""<div class="post-audit-report">
<style>{REPORT_CSS}</style>
<header class="top">
  <div class="kicker">post audit · pipeline output</div>
  <h1>Post audit report</h1>
  <p>{_esc(subtitle)}</p>
</header>
{body}
</div>"""
