# Post Audit

Brief-aware social post audit for the [build-small-hackathon](https://huggingface.co/build-small-hackathon) **Backyard AI** track.

Before you publish, check whether your post actually serves its stated **goal** and **audience** — with deterministic rule linters plus **Gemma 4 E4B** (4.5B effective) on Modal.

## Problem

Community managers and team leads write posts with a goal in mind, but drafts often miss deadlines, bury the lede, or fail to ask for the right action. Manual review is inconsistent. Post Audit gives a structured report: brief check, five scored dimensions, catalogued warnings, and rewrite hints.

## Architecture

```
Gradio Space (HF)          Modal (L4 GPU)
     │                           │
     ├─ rules.py (sync)          └─ Gemma 4 E4B IT
     ├─ merge.py (scores)
     └─ render.py (report UI)
```

- **Rule linters** on the Space: hashtags, chat-dump format, bare links, deadlines, etc.
- **LLM audit** on Modal: goal alignment judgment, tone, CTA clarity, rewrite hints
- **Host recomputes** `overall` and `cappedBy` — never trusts model arithmetic

Model: `google/gemma-4-E4B-it` — **4.5B effective**, Tiny Titan eligible, ≤32B hackathon limit.

## Repository layout

| Path | Purpose |
|------|---------|
| [space/app.py](space/app.py) | Gradio Space UI |
| [space/rules.py](space/rules.py) | Deterministic warnings |
| [space/merge.py](space/merge.py) | Merge + score recomputation |
| [space/prompts.py](space/prompts.py) | LLM system prompt (LLM codes only) |
| [space/render.py](space/render.py) | Report HTML for Gradio |
| [modal_app/inference.py](modal_app/inference.py) | Modal Gemma 4 deployment |
| [post-audit-skill.md](post-audit-skill.md) | Original spec (reference) |

## Local development

Requires [`uv`](https://docs.astral.sh/uv/). The Python version is pinned in
`.python-version` (3.13); the Space SDK's Gradio version is pinned in
[space/requirements.txt](space/requirements.txt) so local runs match the
deployed Space. Your system `python3` may be too old for Gradio 5.x — let `uv`
manage the interpreter.

```bash
make venv     # create .venv (3.13) and install space + modal deps
make test     # unit tests
make smoke    # offline pipeline: rules + mock LLM + merge + render
make dev      # Gradio app with hot reload at http://localhost:7860
```

`make help` lists every task. Without `MODAL_AUDIT_URL`, the app uses a **mock
LLM** (few-shot-shaped responses) so the UI, rules, and rendering are fully
testable offline.

### Iterating against a local LLM (Ollama)

Run a real model on your machine — no Modal credits, no GPU — to exercise the
full prompt → JSON → merge pipeline. Uses [Ollama](https://ollama.com).

```bash
make pull-model      # downloads gemma3:4b (3.3 GB) — fits comfortably in 16 GB RAM
make dev-local       # launches the app wired to the local model
```

The backend is selected by `OLLAMA_MODEL`: when set (and `MODAL_AUDIT_URL` is
not), [audit_client.py](space/audit_client.py) builds the same messages as the
Modal service and POSTs them to Ollama's `/api/chat` with JSON-constrained
output. Override the model — e.g. for production parity at the cost of more
RAM/slower first token:

```bash
make pull-model OLLAMA_MODEL=gemma4:e4b    # ~9.6 GB, tight on 16 GB
make dev-local   OLLAMA_MODEL=gemma4:e4b
```

`OLLAMA_URL` (default `http://localhost:11434`) points at a remote Ollama host
if you run the model elsewhere; `OLLAMA_TIMEOUT` (default 300s) bounds a call.
Precedence is **Modal → Ollama → mock**.

**Speed:** local inference is slow — a full audit is ~2.5 min on an M1/16 GB
with `gemma3:4b` (large few-shot prompt + ~600-token JSON), and the first call
adds model-load time. For a snappier edit loop where output quality doesn't
matter (you're testing plumbing, not the model), use a smaller model:

```bash
make dev-local OLLAMA_MODEL=gemma3:1b    # much faster, lower-quality output
```

### Iterating against the live model

`modal serve` gives you a hot-reloading GPU endpoint without a full deploy:

```bash
make serve-modal                              # prints an ephemeral *.modal.run URL
export MODAL_AUDIT_URL=https://…modal.run     # in another shell
make dev                                       # the local app now calls real Gemma 4
make smoke-remote                              # end-to-end check against the endpoint
```

Prefer the manual commands? They're in the [Makefile](Makefile) — e.g.
`cd space && ../.venv/bin/gradio app.py` for hot reload.

## Deploy Modal

```bash
pip install modal
modal setup   # once
./scripts/deploy_modal.sh
```

Copy the deployed web URL. Create a Modal secret `huggingface` with `HF_TOKEN` if the model requires authentication.

## Deploy Hugging Face Space

1. Create a Space under `build-small-hackathon` (Gradio SDK).
2. Upload contents of `space/` to the Space repo root (`app.py`, `requirements.txt`, etc.).
3. Add Space secret: `MODAL_AUDIT_URL` = Modal endpoint base URL (e.g. `https://you--post-audit-inference-audit-endpoint.modal.run`).

## Demo script (2–3 min video)

1. Open the Space; load **weak webinar CTA** example.
2. Run audit — note rule warnings (hashtag stuffing, no deadline) and LLM warnings (goal mismatch).
3. Walk through the report: score gauge, dimensions, warnings, rewrite hints.
4. Load **chat dump** example — show critical caps and mixed-message warnings.
5. Mention: Gemma 4 E4B on Modal, hybrid rules + LLM, ≤32B.

## Social post template

> Built for #buildSmallHackathon: **Post Audit** — audit your social post against goal & audience before you publish. Hybrid rule linters + Gemma 4 E4B on @Modal. Try it: [SPACE_URL]

## Hackathon checklist

- [ ] Gradio app on HF Space under `build-small-hackathon`
- [ ] Model ≤32B (Gemma 4 E4B)
- [ ] Demo video uploaded
- [ ] Social post published
- [ ] `MODAL_AUDIT_URL` secret set on Space

## License

Apache 2.0 — see [LICENSE](LICENSE).
