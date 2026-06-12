#!/usr/bin/env bash
# Local smoke test: rules + mock LLM + merge + HTML render (no Gradio server).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/space"

echo "== unit tests =="
python3 -m unittest discover -s tests -v

echo ""
echo "== mock audit pipeline =="
python3 - <<'PY'
from audit_client import call_modal_audit
from examples import EXAMPLE_WEBINAR, EXAMPLE_CHAT_DUMP
from merge import merge_audit, viewer_payload
from render import render_report_html
from rules import run_rules

for name, ex in [("webinar", EXAMPLE_WEBINAR), ("chat_dump", EXAMPLE_CHAT_DUMP)]:
    rules = run_rules(ex["platform"], ex["goal"], ex["audience"], ex["post"])
    llm = call_modal_audit(ex["platform"], ex["goal"], ex["audience"], ex["post"])
    merged = merge_audit(llm, rules)
    view = viewer_payload(merged)
    html = render_report_html(view)
    assert "post-audit-report" in html
    audit = merged.get("auditReport")
    n_warn = len(audit["warnings"]) if audit else 0
    print(f"  {name}: rules={len(rules)} warnings={n_warn} html_len={len(html)}")

print("OK")
PY

echo ""
echo "Smoke test passed."
