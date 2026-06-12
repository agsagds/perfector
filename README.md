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

```bash
cd space
pip install -r requirements.txt
python -m unittest discover -s tests -v
python app.py
```

Without `MODAL_AUDIT_URL`, the Space uses a **mock LLM** (few-shot-shaped responses) so UI and rules are testable offline.

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
