# Qwen3-Embedding-8B-Q4_K_M.gguf

Model weights for [Qwen3-Embedding-8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B), the 8B
multilingual text embedding model from the Qwen team (Alibaba Group) -- No.1 on the MTEB
multilingual leaderboard at release (June 2025, score 70.58) -- quantized to Q4_K_M by the model
authors and published in
[Qwen/Qwen3-Embedding-8B-GGUF](https://huggingface.co/Qwen/Qwen3-Embedding-8B-GGUF).

**Why Q4_K_M and not Q8_0 for this size:** the official Q8_0 build is 8.05 GB, above the Snap
Store's 5 GiB per-component limit; shipping it would require splitting the weights across two
sharded components (as canonical's glm-4.7-flash snap does). Q4_K_M (4.68 GB) is the largest
official quantization that ships as a single component, keeping the snap simple. A sharded Q8_0
variant is documented as a possible future addition (see `ai/07-decisoes.md`, DEC-03).

The weights are **not** committed (`.gitignore` excludes `*.gguf`). `make init-all` downloads them
into this directory and verifies the pinned checksum:

```shell
make download-extra-models   # hf download $(GGUF_8B_REPO) $(GGUF_8B_FILE) --local-dir components/model-8b-q4-k-m-gguf
make verify-extra-models     # sha256sum --check against GGUF_8B_SHA256 in the Makefile
```

To build offline (or from an internal mirror), place the file here yourself and run
`make verify-extra-models`; the `GGUF_8B_REPO`/`GGUF_8B_FILE`/`GGUF_8B_SHA256` variables in the
`Makefile` are overridable.

| Field | Value |
| --- | --- |
| File | `Qwen3-Embedding-8B-Q4_K_M.gguf` |
| Size | 4 676 804 928 bytes (4.68 GB) |
| sha256 | `3fcd3febec8b3fd64435204db75bf0dd73b91e8d0661e0331acfe7e7c3120b85` |
| Quantization | Q4_K_M (single file, no shards) |
| GGUF metadata | `general.architecture=qwen3`, `qwen3.pooling_type=3` (LAST), ctx 40960, dim 4096 |
| License | Apache-2.0 (Qwen team, Alibaba Group) |

Single-file GGUF, so `models/qwen3-embedding-8b/model.yaml` needs no `layout`/symlinks: the weight
is mounted by the `model-8b-q4-k-m-gguf` component at `$SNAP_COMPONENTS/model-8b-q4-k-m-gguf/` and
exposed as `MODEL_FILE`.

## Why this README is tracked

`snap/snapcraft.yaml` has a `local-component-files` part with `source: components`. Keeping this
directory in git makes a fresh clone buildable (and fails with a clear "file not found" instead of
a missing source directory) while the 4.68 GB weight stays out of the repository. The part
organizes only the `.gguf` into the component and prunes everything else, so this file is never
shipped inside the snap.
