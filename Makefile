SHELL := /bin/bash

# Always run `hf` via pipx to avoid relying on local `hf` installations.
hf := pipx run --spec "huggingface_hub[cli]" hf

SNAP_NAME ?= qwen3-embedding
ENGINE ?= cpu

# Default model: Qwen3-Embedding-0.6B Q8_0 (official Qwen GGUF).
# The official 0.6B repo publishes only Q8_0 and F16; Q8_0 is near-lossless
# and small (~639 MB), so it is the default. Checksums pinned from the
# downloaded files (see components/*/README.md).
GGUF_06B_REPO ?= Qwen/Qwen3-Embedding-0.6B-GGUF
GGUF_06B_FILE ?= Qwen3-Embedding-0.6B-Q8_0.gguf
GGUF_06B_SHA256 ?= 06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439
MODEL_06B_DIR := components/model-0-6b-q8-0-gguf

# Additional sizes: 4B (Q8_0) and 8B (Q4_K_M), both official Qwen GGUFs.
# The 8B Q8_0 (8.05 GB) exceeds the Snap Store 5 GiB per-component limit, so
# the 8B ships as Q4_K_M (4.68 GB), the largest official quant that fits.
GGUF_4B_REPO ?= Qwen/Qwen3-Embedding-4B-GGUF
GGUF_4B_FILE ?= Qwen3-Embedding-4B-Q8_0.gguf
GGUF_4B_SHA256 ?= b60ae5ce2dd6a0b77f82cadf21def1f310a3e10cde380ad0081b07a9d416949d
MODEL_4B_DIR := components/model-4b-q8-0-gguf

GGUF_8B_REPO ?= Qwen/Qwen3-Embedding-8B-GGUF
GGUF_8B_FILE ?= Qwen3-Embedding-8B-Q4_K_M.gguf
GGUF_8B_SHA256 ?= 3fcd3febec8b3fd64435204db75bf0dd73b91e8d0661e0331acfe7e7c3120b85
MODEL_8B_DIR := components/model-8b-q4-k-m-gguf

.PHONY: all help init init-all build install upload smoke-test embed-test install-deps init-submodules download-models download-extra-models verify-model verify-extra-models

all: help

#
# Main targets
#

help: ## Show this help message
	@echo "Usage: make <target>"
	@echo
	@echo "Targets:"
	@# List all targets with descriptions (lines starting with '##'):
	@grep -E '^[a-zA-Z0-9_-]+:.*## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  %-18s %s\n", $$1, $$2}'

init: init-submodules install-deps download-models verify-model ## Initialize the build environment (default 0.6B model only)

init-all: init-submodules install-deps download-models download-extra-models verify-model verify-extra-models ## Initialize with all model sizes (0.6B, 4B, 8B)

build: ## Build the snap (needs all model files; use init-all first)
	./dev/build.sh

install: ## Install the snap
	./dev/install.sh

upload: ## Upload the snap
	./dev/upload.sh

smoke-test: ## Run smoke tests (override with SNAP_NAME=... ENGINE=...)
	sudo ./dev/smoke-test.sh $(SNAP_NAME) $(ENGINE)

embed-test: ## Run the embeddings E2E battery against a running server (PORT=..., MODEL=..., DIM=...)
	python3 tests/embeddings-e2e.py http://127.0.0.1:$(or $(PORT),8362) $(or $(MODEL),qwen3-embedding-0-6b) $(or $(DIM),1024)

#
# Supporting targets
#

install-deps:
	@echo "Installing dependencies..."
	@# Ensure pipx is available for running the hf CLI.
	@command -v pipx >/dev/null 2>&1 || { \
		sudo apt-get update; \
		sudo apt-get install -y pipx; \
	}

init-submodules:
	@echo "Initializing submodules..."
	@if git submodule status | grep -q '^-'; then \
		git submodule update --init; \
	fi

download-models:
	@echo "Downloading Qwen3-Embedding-0.6B-Q8_0 model weights (~0.6 GB)..."
	$(hf) download $(GGUF_06B_REPO) $(GGUF_06B_FILE) \
		--local-dir $(MODEL_06B_DIR)

download-extra-models: ## Download the 4B and 8B model weights (~9 GB total)
	@echo "Downloading Qwen3-Embedding-4B-Q8_0 model weights (~4.3 GB)..."
	$(hf) download $(GGUF_4B_REPO) $(GGUF_4B_FILE) \
		--local-dir $(MODEL_4B_DIR)
	@echo "Downloading Qwen3-Embedding-8B-Q4_K_M model weights (~4.7 GB)..."
	$(hf) download $(GGUF_8B_REPO) $(GGUF_8B_FILE) \
		--local-dir $(MODEL_8B_DIR)

verify-model: ## Verify the 0.6B GGUF checksum against the pinned sha256
	@echo "Verifying $(MODEL_06B_DIR)/$(GGUF_06B_FILE)..."
	@if [ ! -f "$(MODEL_06B_DIR)/$(GGUF_06B_FILE)" ]; then \
		echo "ERROR: $(MODEL_06B_DIR)/$(GGUF_06B_FILE) not found. Run 'make download-models' first." >&2; \
		exit 1; \
	fi
	@echo "$(GGUF_06B_SHA256)  $(MODEL_06B_DIR)/$(GGUF_06B_FILE)" | sha256sum --check --status \
		&& echo "OK: 0.6B checksum matches" \
		|| { echo "ERROR: 0.6B checksum mismatch (expected $(GGUF_06B_SHA256))" >&2; exit 1; }

verify-extra-models: ## Verify the 4B and 8B GGUF checksums
	@echo "Verifying $(MODEL_4B_DIR)/$(GGUF_4B_FILE)..."
	@if [ ! -f "$(MODEL_4B_DIR)/$(GGUF_4B_FILE)" ]; then \
		echo "ERROR: $(MODEL_4B_DIR)/$(GGUF_4B_FILE) not found. Run 'make download-extra-models' first." >&2; \
		exit 1; \
	fi
	@echo "$(GGUF_4B_SHA256)  $(MODEL_4B_DIR)/$(GGUF_4B_FILE)" | sha256sum --check --status \
		&& echo "OK: 4B checksum matches" \
		|| { echo "ERROR: 4B checksum mismatch (expected $(GGUF_4B_SHA256))" >&2; exit 1; }
	@echo "Verifying $(MODEL_8B_DIR)/$(GGUF_8B_FILE)..."
	@if [ ! -f "$(MODEL_8B_DIR)/$(GGUF_8B_FILE)" ]; then \
		echo "ERROR: $(MODEL_8B_DIR)/$(GGUF_8B_FILE) not found. Run 'make download-extra-models' first." >&2; \
		exit 1; \
	fi
	@echo "$(GGUF_8B_SHA256)  $(MODEL_8B_DIR)/$(GGUF_8B_FILE)" | sha256sum --check --status \
		&& echo "OK: 8B checksum matches" \
		|| { echo "ERROR: 8B checksum mismatch (expected $(GGUF_8B_SHA256))" >&2; exit 1; }
