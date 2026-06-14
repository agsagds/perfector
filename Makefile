# Post Audit — local development tasks.
# Requires `uv` (https://docs.astral.sh/uv/). Python version is pinned in .python-version.

VENV        := .venv
PY          := $(VENV)/bin/python
OLLAMA_MODEL ?= gemma4:e4b

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# Recreate the venv from scratch whenever a requirements file changes, so deps
# dropped from the requirements (e.g. torch, removed from modal_app) don't
# linger. `uv pip install` only adds/upgrades, never prunes; `uv pip sync` is
# not usable here because these files list only top-level requirements and it
# would drop their (unlisted) transitive deps.
$(VENV): .python-version space/requirements.txt modal_app/requirements.txt
	rm -rf $(VENV)
	uv venv
	uv pip install -r space/requirements.txt -r modal_app/requirements.txt
	@touch $(VENV)

.PHONY: venv
venv: $(VENV) ## Create/refresh the local virtualenv with all deps

.PHONY: test
test: $(VENV) ## Run unit tests
	cd space && ../$(PY) -m unittest discover -s tests -v

.PHONY: smoke
smoke: $(VENV) ## Run the offline smoke test (rules + mock LLM + render)
	./scripts/smoke_local.sh

# Run via `python app.py` (not the `gradio` CLI): theme/css are applied in the
# app's own .launch() call, which the CLI's reload runner bypasses — so the CLI
# would serve the app without its theme. This matches how HF Spaces runs it.
.PHONY: dev
dev: $(VENV) ## Launch the Gradio app (mock LLM unless MODAL_AUDIT_URL is set)
	cd space && ../$(PY) app.py

.PHONY: pull-model
pull-model: ## Download the local Ollama model (default gemma4:e4b — same as prod)
	ollama pull $(OLLAMA_MODEL)

.PHONY: dev-local
dev-local: $(VENV) ## Launch the app wired to a local Ollama model (override OLLAMA_MODEL=...)
	cd space && OLLAMA_MODEL=$(OLLAMA_MODEL) ../$(PY) app.py

.PHONY: serve-modal
serve-modal: $(VENV) ## Hot-reloading ephemeral Modal endpoint for live Gemma 4 (needs `modal setup`)
	$(VENV)/bin/modal serve modal_app/inference.py

.PHONY: smoke-remote
smoke-remote: $(VENV) ## Hit a live Modal endpoint end-to-end (requires MODAL_AUDIT_URL)
	$(PY) scripts/smoke_remote.py

.PHONY: clean
clean: ## Remove the virtualenv and caches
	rm -rf $(VENV)
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
