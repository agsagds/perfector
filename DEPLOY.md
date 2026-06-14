# Deploy checklist

Run these on a machine with `pip`, `modal`, and `hf` CLI authenticated.

## 1. Local verification

```bash
./scripts/smoke_local.sh
```

## 2. Modal

```bash
pip install modal
modal setup
# Deploy. Set AUDIT_TOKEN to require an X-Audit-Token header (recommended for
# anything public — the check runs in the CPU web function before the GPU spins
# up, so unauthorized calls don't burn credits). Leave it unset for an open endpoint.
AUDIT_TOKEN=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))') \
  ./scripts/deploy_modal.sh
```

Copy the printed `audit_endpoint` URL. The first request pulls the quantized
`gemma4:e4b` GGUF into a Modal Volume (~6 GB, cached thereafter), so the very
first cold start is slow; later ones reuse the cached weights.

There's **one deployment** — the same artifact serves everyone. To run a
throwaway dev endpoint, use `make serve-modal` (ephemeral, hot-reload); to
separate staging from prod, deploy with a different `AUDIT_TOKEN` (and, if you
want a distinct URL, pass an environment: `./scripts/deploy_modal.sh prod` after
`modal environment create prod`). A separate environment is optional, not
required — tokens are the access control.

## 3. Hugging Face Space

Create Space under `build-small-hackathon` (Gradio, public).

Upload **contents of `space/`** to the Space repo root:

```bash
cd space
git init
git remote add space https://huggingface.co/spaces/build-small-hackathon/post-audit
git add app.py requirements.txt README.md *.py static/
git commit -m "Post Audit MVP"
git push space main
```

In Space **Settings → Repository secrets**:

| Key | Value |
|-----|--------|
| `MODAL_AUDIT_URL` | Modal endpoint URL (the endpoint is served at the URL root — no path suffix) |
| `MODAL_AUDIT_TOKEN` | (optional) same value as `AUDIT_TOKEN` used at Modal deploy time |

## 4. Remote smoke

```bash
export MODAL_AUDIT_URL=https://YOUR-WORKSPACE--post-audit-inference-audit-endpoint.modal.run
export MODAL_AUDIT_TOKEN=...   # if the endpoint is token-protected
python3 scripts/smoke_remote.py
```

The first request on a fresh deploy cold-starts the container and pulls the
quantized GGUF (~6 GB) into the Volume; once cached, cold starts just load it.
The client timeout defaults to 300s and is configurable via `MODAL_AUDIT_TIMEOUT`.

## 5. Submission

See [SUBMISSION.md](SUBMISSION.md) for demo video script and social post template.
