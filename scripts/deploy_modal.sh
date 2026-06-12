#!/usr/bin/env bash
# Deploy Modal inference and print endpoint URL.
set -euo pipefail
cd "$(dirname "$0")/.."
modal deploy modal/inference.py
echo ""
echo "Set HF Space secret MODAL_AUDIT_URL to the web endpoint URL printed above (base URL, no /audit suffix)."
