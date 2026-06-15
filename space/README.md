---
title: Perfector
emoji: 📋
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "6.18.0"
app_file: app.py
pinned: false
license: apache-2.0
short_description: Audit posts against goal & audience (Gemma 4 + rules)
tags:
  - build-small-hackathon
  - backyard-ai
  - gradio
  - gemma
  - llama-cpp
  - modal
  - track:backyard
  - sponsor:modal
  - llama-champion
  - field-notes
  - off-brand
  - achievement:llama
  - achievement:fieldnotes
  - achievement:offbrand
---

# Perfector

> **Note:** This Space is a clone of [build-small-hackathon/post-audit](https://huggingface.co/spaces/build-small-hackathon/post-audit). The original maintainer was not available to apply submission updates before the hackathon freeze, so this copy hosts the final README, demo links, and tags for judging.

Brief-aware social post audit for the [build-small-hackathon](https://huggingface.co/build-small-hackathon) **Backyard AI** track.

Before you publish, check whether your draft actually serves its stated **goal** and **audience** — with deterministic rule linters plus **Gemma 4 E4B** (4.5B effective) on Modal.

**Model:** Gemma 4 E4B (4.5B effective parameters, ≤32B hackathon limit)  
**Inference:** Modal L4 GPU (Ollama / llama.cpp, quantized GGUF)  
**Host:** Rule linters + deterministic score recomputation

## Demo video

- [Post Audit demo — Eugene Pasternak](https://youtu.be/Hd1deTByJFg)
- [Post Audit demo — Pavel Trubin](https://youtu.be/j7XnzXBj5-I)

## Social post

[LinkedIn announcement](https://www.linkedin.com/posts/eugene-pasternak-9318b038_buildsmallhackathon-huggingface-gradio-ugcPost-7471886308513140736-dcDj/)

## Field notes

[Field Notes: Post Audit — a brief-aware social-post auditor in 4.5B params](https://huggingface.co/blog/build-small-hackathon/post-audit-demo-article)

## Links


| | |
|---|---|
| Source code | [github.com/agsagds/perfector](https://github.com/agsagds/perfector) |
| Original Space | [build-small-hackathon/post-audit](https://huggingface.co/spaces/build-small-hackathon/post-audit) |
| This Space (submission copy) | [build-small-hackathon/perfector](https://huggingface.co/spaces/build-small-hackathon/perfector) |


Set Space secret `MODAL_AUDIT_URL` to your deployed Modal web endpoint base URL (without trailing `/audit`).

## Team

- Eugene Pasternak — [`pasternake`](https://huggingface.co/pasternake)
- Pavel Trubin — [`agsagds`](https://huggingface.co/agsagds)

