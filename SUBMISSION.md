# Submission assets

## Demo video outline (2–3 minutes)

1. **Hook (15s):** "You wrote a post with a goal — but does the draft actually drive that action?"
2. **Example A (60s):** Load weak webinar CTA → Run audit → show score, HASHTAG_STUFFING, NO_DEADLINE, GOAL_ACTION_MISMATCH, rewrite hints.
3. **Example B (45s):** Chat dump → critical cap, structure warnings.
4. **Stack (20s):** Gemma 4 E4B on Modal, rule linters on host, custom report UI.
5. **Close (10s):** Space URL + hackathon tags.

## Social post (copy-paste)

```
Built for the Hugging Face build-small hackathon 🏡

Post Audit — check your social draft against your stated goal and audience before you publish.

Hybrid pipeline:
• deterministic rule linters (hashtags, chat dumps, deadlines…)
• Gemma 4 E4B (4.5B effective) on Modal for judgment + rewrite hints

Try it: https://huggingface.co/spaces/build-small-hackathon/post-audit

#buildSmallHackathon #Gradio #Modal #Gemma
```

## Space secrets

| Name | Value |
|------|--------|
| `MODAL_AUDIT_URL` | Modal `audit_endpoint` base URL from `modal deploy` output |

## Pre-recording warm-up

Run audit once on the webinar example ~2 minutes before recording so Modal GPU is warm and the demo feels snappy.
