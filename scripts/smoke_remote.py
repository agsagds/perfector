#!/usr/bin/env python3
"""Smoke test against live Modal endpoint (requires MODAL_AUDIT_URL)."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "space"))

from audit_client import call_modal_audit  # noqa: E402
from examples import EXAMPLE_WEBINAR  # noqa: E402
from merge import merge_audit, viewer_payload  # noqa: E402
from rules import run_rules  # noqa: E402

url = os.environ.get("MODAL_AUDIT_URL")
if not url:
    print("Set MODAL_AUDIT_URL to the Modal endpoint base URL", file=sys.stderr)
    sys.exit(1)

ex = EXAMPLE_WEBINAR
rules = run_rules(ex["platform"], ex["goal"], ex["audience"], ex["post"])
llm = call_modal_audit(ex["platform"], ex["goal"], ex["audience"], ex["post"])
merged = merge_audit(llm, rules)
view = viewer_payload(merged)
assert view.get("goalAlignment") or view.get("status")
print("Remote audit OK:", url)
print("Overall:", view.get("goalAlignment", {}).get("overall"))
