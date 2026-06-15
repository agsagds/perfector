#!/usr/bin/env bash
# Publish space/ to build-small-hackathon/perfector on Hugging Face.
# Requires: hf CLI + write-scoped HF token (hf auth whoami must succeed).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SPACE_ID="build-small-hackathon/perfector"
SPACE_DIR="$ROOT/space"

if ! command -v hf >/dev/null 2>&1; then
  echo "Install the Hugging Face CLI: curl -LsSf https://hf.co/cli/install.sh | bash -s" >&2
  exit 1
fi

if ! hf auth whoami >/dev/null 2>&1; then
  echo "Not logged in. Run: hf auth login --token <WRITE_TOKEN> --add-to-git-credential" >&2
  exit 1
fi

echo "Logged in as: $(hf auth whoami | sed -n 's/^user=//p')"

if ! hf repos info "$SPACE_ID" --repo-type space >/dev/null 2>&1; then
  echo "Creating Space $SPACE_ID ..."
  hf repos create "$SPACE_ID" \
    --type space \
    --space-sdk gradio \
    --public \
    --flavor cpu-basic \
    --exist-ok
else
  echo "Space $SPACE_ID already exists."
fi

echo "Uploading files from $SPACE_DIR ..."
hf upload "$SPACE_ID" "$SPACE_DIR" . \
  --repo-type space \
  --exclude "tests/*" \
  --exclude "**/__pycache__/*" \
  --exclude ".git/*" \
  --commit-message "Publish Perfector submission copy (Post Audit clone)"

echo
echo "Uploaded: https://huggingface.co/spaces/$SPACE_ID"
echo
echo "Next: copy Modal secrets from post-audit (values are write-only; set manually):"
echo "  hf spaces secrets list build-small-hackathon/post-audit"
echo "  hf spaces secrets add $SPACE_ID -s MODAL_AUDIT_URL=<same-as-post-audit> -s MODAL_AUDIT_TOKEN=<same-as-post-audit>"
echo
echo "Or duplicate from the HF UI: Space Settings → Duplicate this Space → perfector"
