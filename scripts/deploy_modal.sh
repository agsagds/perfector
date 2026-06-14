#!/usr/bin/env bash
# Deploy the Modal inference app and print the endpoint URL.
#
# Usage:
#   ./scripts/deploy_modal.sh [modal-environment]   # default: main
#
# Set AUDIT_TOKEN to require an X-Audit-Token header on every request (recommended
# for any shared/prod endpoint). Leave it unset to deploy an open endpoint.
#
#   AUDIT_TOKEN=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))') \
#     ./scripts/deploy_modal.sh prod
set -euo pipefail
cd "$(dirname "$0")/.."

ENVIRONMENT="${1:-main}"

modal deploy -e "$ENVIRONMENT" modal_app/inference.py
echo ""
echo "Deployed to Modal environment: $ENVIRONMENT"
echo "Set the HF Space secret MODAL_AUDIT_URL to the web endpoint URL printed above"
echo "(the endpoint is served at the URL root — no path suffix)."
if [ -n "${AUDIT_TOKEN:-}" ]; then
  echo "Endpoint is token-protected. Set the Space secret MODAL_AUDIT_TOKEN to the same value."
fi
