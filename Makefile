# Post Audit — local development tasks.
# Requires `uv` (https://docs.astral.sh/uv/). Python version is pinned in .python-version.

VENV := .venv
PY   := $(VENV)/bin/python

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

$(VENV): .python-version space/requirements.txt modal_app/requirements.txt
	uv venv --allow-existing
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

.PHONY: dev
dev: $(VENV) ## Launch the Gradio app with hot reload (mock LLM unless MODAL_AUDIT_URL is set)
	cd space && ../$(VENV)/bin/gradio app.py

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
