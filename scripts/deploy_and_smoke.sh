#!/usr/bin/env bash
# Deploy Modal + verify endpoint responds (requires modal CLI auth).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v modal >/dev/null 2>&1; then
  echo "Installing modal..."
  pip install modal
fi

"$ROOT/scripts/deploy_modal.sh"

echo ""
echo "After deploy, set MODAL_AUDIT_URL on your HF Space and run:"
echo "  MODAL_AUDIT_URL=https://your-endpoint.modal.run python3 scripts/smoke_remote.py"
