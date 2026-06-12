---
title: Post Audit
emoji: 📋
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "5.12.0"
app_file: app.py
pinned: false
license: apache-2.0
short_description: Audit social posts against goal and audience (Gemma 4 E4B + rules)
---

# Post Audit

Brief-aware social post audit for the [build-small-hackathon](https://huggingface.co/build-small-hackathon) Backyard AI track.

**Model:** Gemma 4 E4B (4.5B effective parameters, ≤32B hackathon limit)  
**Inference:** Modal GPU endpoint  
**Host:** Rule linters + deterministic score recomputation

Set Space secret `MODAL_AUDIT_URL` to your deployed Modal web endpoint base URL (without trailing `/audit`).
