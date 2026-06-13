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
./scripts/deploy_modal.sh
```

Copy the `audit_endpoint` URL from deploy output.

Optional: create Modal secret `huggingface` with `HF_TOKEN` if model download requires it:

```bash
modal secret create huggingface HF_TOKEN=hf_...
```

Then add `secrets=[modal.Secret.from_name("huggingface")]` to `@app.cls` in `modal_app/inference.py`.

Optional: protect the endpoint with a shared secret — export `AUDIT_TOKEN=<random string>` before running `./scripts/deploy_modal.sh`. When set, every request must carry a matching `X-Audit-Token` header (the Space sends it automatically when its `MODAL_AUDIT_TOKEN` secret is set to the same value).

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
python3 scripts/smoke_remote.py
```

## 5. Submission

See [SUBMISSION.md](SUBMISSION.md) for demo video script and social post template.
