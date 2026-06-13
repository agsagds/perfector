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
```

### Environments (dev / prod split)

Deploys are scoped to a Modal **environment**. Keep prod isolated from dev/staging:

```bash
modal environment create prod          # once
# prod: token-protected, its own endpoint URL
AUDIT_TOKEN=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))') \
  ./scripts/deploy_modal.sh prod
# dev/staging in the default 'main' env (also protect it):
AUDIT_TOKEN=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))') \
  ./scripts/deploy_modal.sh main
```

Each environment gets a distinct `audit_endpoint` URL — copy the one for the
environment you're wiring to the Space. **Use a different `AUDIT_TOKEN` per
environment** so a leaked dev token can't reach prod. For local iteration, prefer
`make serve-modal` (ephemeral) or the Ollama path — don't point local dev at prod.

> The endpoint checks the token in the lightweight CPU web function **before**
> invoking the GPU, so unauthorized requests are rejected without burning credits.

Optional: create Modal secret `huggingface` with `HF_TOKEN` if model download requires it:

```bash
modal secret create huggingface HF_TOKEN=hf_...
```

Then add `secrets=[modal.Secret.from_name("huggingface")]` to `@app.cls` in `modal_app/inference.py`.

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

The first request cold-starts the container (downloads + loads the ~16 GB model,
~2 min); warm latency is ~50s. The client timeout defaults to 300s and is
configurable via `MODAL_AUDIT_TIMEOUT`.

## 5. Submission

See [SUBMISSION.md](SUBMISSION.md) for demo video script and social post template.
