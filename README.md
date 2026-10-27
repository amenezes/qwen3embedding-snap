# Qwen3 Embedding inference snap

[![qwen3-embedding](https://snapcraft.io/qwen3-embedding/badge.svg)](https://snapcraft.io/qwen3-embedding)

<!-- README-I18N:START -->

**English** | [Português (Brasil)](./README.pt-BR.md) | [简体中文](./README.zh-CN.md)

<!-- README-I18N:END -->

**[Qwen3-Embedding](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)** is the
[Qwen team](https://qwen.ai)'s family of text embedding models, purpose-built for retrieval,
semantic search, RAG pipelines, classification, clustering and code search. It supports 100+
languages (including programming languages), 32K-token inputs, user-defined output dimensions
(Matryoshka) and task-specific instructions. The 8B variant ranked **No.1 on the MTEB
multilingual leaderboard** at release (June 2025, score 70.58).

Use this snap to quickly install an optimized environment for local text embedding with
Qwen3-Embedding, served through an OpenAI-compatible `/v1/embeddings` API.

The snap includes the following hardware-optimized inference engines:

* cpu: Optimized for x64 and ARM (armv8, armv9) CPUs
* nvidia-gpu: CUDA-enabled GPU acceleration
* amd-gpu: ROCm-enabled GPU acceleration for AMD GPUs

The most suitable engine is automatically selected based on the available hardware.

#### Install
```shell
sudo snap install qwen3-embedding
```

#### Use
```shell
curl -s http://127.0.0.1:8362/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "qwen3-embedding-0-6b", "input": "What is an inference snap?"}'
```

> [!TIP]
> Some accelerators require extra [drivers](https://documentation.ubuntu.com/inference-snaps/how-to/setup/drivers/) to be usable with this snap.
> The `amd-gpu` engine uses the in-kernel `amdgpu` driver (KFD); the ROCm
> user-space libraries are bundled in the snap, so no host ROCm install is needed.

## Model sizes

Three sizes are available. The 0.6B is the default; switch with
`sudo qwen3-embedding use-model <model>` and restart the service:

| Model | Weights | Disk (installed) | Embedding dim | Notes |
| --- | --- | --- | --- | --- |
| `qwen3-embedding-0-6b` (Q8_0) | 0.64 GB | ~1.0 GB | 1024 | Fast, edge/RAG; near-lossless quant |
| `qwen3-embedding-4b` (Q8_0) | 4.28 GB | ~4.7 GB | 2560 | Higher retrieval quality |
| `qwen3-embedding-8b` (Q4_K_M) | 4.68 GB | ~5.1 GB | 4096 | Top quality (MTEB multilingual No.1) |

```shell
sudo qwen3-embedding use-model qwen3-embedding-4b
sudo snap restart qwen3-embedding
```

All weights are official GGUFs published by the Qwen team
([0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF),
[4B](https://huggingface.co/Qwen/Qwen3-Embedding-4B-GGUF),
[8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B-GGUF)). The 0.6B and 4B ship at Q8_0
(near-lossless); the 8B ships at Q4_K_M because the official Q8_0 build (8.05 GB) exceeds the
Snap Store's 5 GiB per-component limit and would need weight sharding.

## Requirements

Measured on the cpu engine as the peak RSS of `llama-server` with the pinned llama.cpp runtime.
The context is fitted to the available memory (`--fit-ctx`, 4096-token floor, 32K ceiling), so
the KV cache -- and therefore the memory footprint -- scales with both free RAM and model size:

| Model | Weights | KV cache (4096 → 32768 tokens) | Typical total RSS |
| --- | --- | --- | --- |
| 0.6B | 0.64 GB | 0.45 → 3.6 GB | ~1.4 → 4.6 GB |
| 4B | 4.28 GB | 0.60 → 4.8 GB | ~5.2 → 9.4 GB |
| 8B | 4.68 GB | 0.60 → 4.8 GB | ~5.6 → 9.8 GB |

Budget **~110 KB per context token** for the 0.6B and **~147 KB per token** for the 4B/8B on top
of the weights. On the nvidia-gpu engine llama.cpp offloads as many layers as fit in the GPU,
so partial offload is supported.

Disk usage is ~1.0 GB once installed with the 0.6B model (snap + llama.cpp component + weights),
plus ~1.1 GB if the nvidia-gpu engine is selected (~730 MB download), or ~3.8 GB if the amd-gpu
engine is selected (~1.1 GB download).

## Usage guide

### Basic embedding

```shell
curl -s http://127.0.0.1:8362/v1/embeddings -H 'Content-Type: application/json' -d '{
  "model": "qwen3-embedding-0-6b",
  "input": ["What is the capital of China?", "The capital of China is Beijing."]}'
```

Vectors come back **L2-normalized**, so the dot product of two vectors is their cosine
similarity. The response follows the OpenAI embeddings schema (`data[].embedding`,
`data[].index`, `usage.prompt_tokens`).

### Instructions (recommended for retrieval)

Qwen3-Embedding is instruction-aware: prefixing **queries** with a task description improves
retrieval by ~1-5% (vendor measurement; our E2E battery shows a larger margin on small
examples). Documents are embedded as-is:

```shell
INSTRUCT="Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "
curl -s http://127.0.0.1:8362/v1/embeddings -H 'Content-Type: application/json' -d "{
  \"model\": \"qwen3-embedding-0-6b\",
  \"input\": \"${INSTRUCT}Como funciona um snap do Ubuntu?\"}"
```

Write instructions in **English** even for non-English content: most training instructions were
English. Add the instruction to the query side only -- adding it to documents hurts.

### Custom dimensions (Matryoshka)

The models support Matryoshka Representation Learning: the first *N* dimensions of the vector
remain meaningful after truncation + renormalization (0.6B: 32-1024, 4B: up to 2560, 8B: up to
4096). The server always returns the full vector, so truncate client-side:

```python
import math
v = response["data"][0]["embedding"][:256]
v = [x / math.sqrt(sum(t*t for t in v)) for x in v]   # renormalize after truncation
```

The OpenAI `dimensions` request parameter is accepted but **ignored** by the bundled
llama-server (it always returns the full dimension); do the truncation above instead.

### Long documents and batches

* Inputs longer than the fitted context are rejected with HTTP 400
  (`exceed_context_size_error`) instead of being silently truncated -- chunk your documents
  (the model's sweet spot is passages up to a few thousand tokens).
* A single request may embed a list of texts; keep the **total** tokens of a batch within the
  context, or split it into several requests.

## Configuration

The engine reads its settings from the snap configuration:

| Setting | Default | Purpose |
| --- | --- | --- |
| `min-context-size` | `4096` | Floor for `--fit-ctx`; `--fit` grows the context up to the model's 32K limit |
| `sleep-idle-seconds` | `600` | Idle time before `llama-server` unloads the model (frees RAM) |
| `ubatch-size` | `512` | Physical batch for prompt processing (throughput vs RAM trade-off) |
| `http.port` / `http.host` | `8362` / `127.0.0.1` | OpenAI-compatible API |
| `verbose` | `false` | Pass `--verbose` to `llama-server` |

Read them with `qwen3-embedding get`; changing them needs root (`sudo qwen3-embedding set`), and
the service has to be restarted to apply:

```shell
qwen3-embedding get
sudo qwen3-embedding set ubatch-size=8192
sudo snap restart qwen3-embedding
```

Load-gated measurements on CPU (see the repo's `ai/` docs) made **512** -- the llama.cpp
default -- the fastest and lightest choice for every document profile here; larger ubatches
cost a bigger compute buffer (RAM/VRAM) without paying off on this hardware. On GPU, or on
throughput-oriented boxes, the vendor-recommended `ubatch-size=8192` may win: measure before
changing.

## Resources

📚 **[Documentation](https://documentation.ubuntu.com/inference-snaps/)**, learn how to use inference snaps

🤗 **[Model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)**, upstream documentation for the model

📦 **[GGUF weights](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF)**, the quantized weights this snap bundles

🧩 **[Qwen3-Embedding repository](https://github.com/QwenLM/Qwen3-Embedding)**, evaluation code and usage examples

📝 **[Technical report](https://arxiv.org/pdf/2506.05176)**, Qwen3 Embedding: Multilingual, Versatile, Efficient

🐛 **[Issues](https://github.com/amenezes/qwen3embedding-snap/issues)**, report bugs and request features

## Notes on this snap

* **Runtime pin:** llama.cpp is pinned to `b10344`, the build also used by the sibling snaps
  (`minicpm5-2b`, `qwen3guard`) and by Canonical's `phi4`/`smollm2`/`gemma4`. Qwen3 architecture
  support (including the embedding models) landed upstream in May 2025, long before this pin.
  Bumps arrive as reviewed Renovate PRs (never automerged) and must pass the embedding E2E
  battery (`make embed-test`).
* **Pooling:** the engine passes `--pooling last` explicitly -- the last-token (EOS) pooling
  Qwen3-Embedding was trained with. The official GGUFs embed the same value in their metadata
  (`llama.pooling_type=LAST`); the flag keeps re-quantized GGUFs that drop the metadata working.
* **No web UI:** this snap ships no chat interface or webui -- embedding models produce vectors,
  not text. The bundled `llama-server` still answers `/v1/chat/completions` with meaningless
  output (it is a base model); use `/v1/embeddings`.
* **Normalization:** vectors are L2-normalized server-side (llama.cpp `--embd-normalize`
  default), matching the model's intended cosine-similarity usage.
* **Model license:** Apache-2.0 (Qwen team, Alibaba Group). The packaging code is GPL-3.0.
* **Engine selection:** the `nvidia-gpu` and `amd-gpu` engines are picked whenever a GPU
  from the matching vendor is present on the PCI bus, even if the driver is not usable.
  The backend then fails to initialise and llama.cpp falls back to the CPU backend; run
  `sudo qwen3-embedding use-engine cpu` to switch back and free the engine component
  (~1.1 GB NVIDIA, ~3.8 GB AMD). The AMD engine only matches the microarchitectures
  supported by the bundled ROCm build (gfx1010-gfx1201, including the RX 9070 XT);
  older AMD GPUs select the cpu engine. Selection runs at install time and needs the
  `hardware-observe` interface; if its auto-connection has not been granted, connect it
  and re-run the selection manually:
  ```shell
  sudo snap connect qwen3-embedding:hardware-observe
  sudo qwen3-embedding use-engine --auto
  ```
* **AMD engine needs `process-control`:** the ROCm runtime pins its worker threads with
  `sched_setaffinity`, and snapd's default seccomp policy only allows that call for pid 0.
  Without the plug, HSA fails to initialise, llama.cpp reports `no ROCm-capable device is
  detected` and runs on the CPU while the engine still shows `amd-gpu`. The interface is not
  auto-connected, so connect it once after install -- and request its auto-connection before
  publishing to the store:
  ```shell
  sudo snap connect qwen3-embedding:process-control
  sudo snap restart qwen3-embedding.server
  ```
* **Provider:** the snap exports an `inference-provider` content slot, so another snap can
  consume this endpoint instead of running its own model.
* **Local API:** the endpoint has no authentication and allows cross-origin requests. It listens
  on `127.0.0.1` only -- do not rebind `http.host` to a public interface.
* **Port:** 8362 continues the inference-snaps family sequence (8324-8361 are used by
  Canonical's snaps, 8364/8365 by the sibling `qwen3guard` snap).

## Build and install from source

Clone the repo:
```shell
git clone <this-repo>
```

Initialize the development environment:
```shell
make init        # default 0.6B weights (~0.6 GB) + checksum verification
make init-all    # all three sizes (~9.6 GB)
```

`snapcraft` builds inside a container by default, so a build provider must be available first.
With LXD, initialize it once (`--storage-backend=dir` avoids a ZFS loop pool):

```shell
lxd init --auto --storage-backend=dir
```

Without a provider, build on the host with `sudo snapcraft pack --destructive-mode
--platform amd64` instead.

Build and install snap:
```shell
make build       # needs init-all: the three GGUFs become components
make install
```

Validate the running server with the embeddings E2E battery:
```shell
make embed-test                       # against the installed snap (port 8362)
make embed-test MODEL=qwen3-embedding-4b DIM=2560
```

To use local weight copies, place them under `components/model-*-gguf/` and run
`make verify-model` / `make verify-extra-models`; the `GGUF_*` variables in the `Makefile` are
overridable for internal mirrors.

## Publishing to the Snap Store

Two store-side requests are prerequisites, and both take time, so open them early:

* **Component upload access** -- the weights and the llama.cpp runtime ship as
  [components](https://snapcraft.io/docs/explanation/how-snaps-work/snap-components/), and
  uploading components is limited to accounts on the store's allow-list. Request it on the
  [Snapcraft forum](https://forum.snapcraft.io/c/store-requests/).
* **Auto-connection of `hardware-observe`** -- the interface is not auto-connected by default, so
  a store install cannot detect the hardware during `use-engine --auto` until the request is
  granted (see the
  [process](https://snapcraft.io/docs/reference/administration/process-for-aliases-auto-connections-and-tracks/)).

The first upload also requires a registered name, and a repository that actually exists: the store
listing links to `website`, `source-code`, `issues` and `contact` from `snap/snapcraft.yaml`.

```shell
snapcraft login
snapcraft register qwen3-embedding
make build
./dev/upload.sh latest/edge   # snapcraft upload <snap> --component ... --release=latest/edge
```

`.github/workflows/cicd.yaml` publishes to `latest/edge` on every push to `main` once the
`SNAPCRAFT_STORE_CREDENTIALS` secret (the output of `snapcraft export-login`) is configured.
Note the CI runner needs ~25 GB free disk: `make init-all` fetches all three GGUFs because the
build organizes them into components.
