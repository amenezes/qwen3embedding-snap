# Qwen3-Embedding-4B-Q8_0.gguf

Model weights for [Qwen3-Embedding-4B](https://huggingface.co/Qwen/Qwen3-Embedding-4B), the 4B
multilingual text embedding model from the Qwen team (Alibaba Group), quantized to Q8_0 by the
model authors and published in
[Qwen/Qwen3-Embedding-4B-GGUF](https://huggingface.co/Qwen/Qwen3-Embedding-4B-GGUF).

Q8_0 is near-lossless and, at 4.28 GB, still fits the Snap Store's 5 GiB per-component limit as a
single file -- so this size ships at the highest practical quality instead of a more aggressive
quantization.

The weights are **not** committed (`.gitignore` excludes `*.gguf`). `make init-all` downloads them
into this directory and verifies the pinned checksum:

```shell
make download-extra-models   # hf download $(GGUF_4B_REPO) $(GGUF_4B_FILE) --local-dir components/model-4b-q8-0-gguf
make verify-extra-models     # sha256sum --check against GGUF_4B_SHA256 in the Makefile
```

To build offline (or from an internal mirror), place the file here yourself and run
`make verify-extra-models`; the `GGUF_4B_REPO`/`GGUF_4B_FILE`/`GGUF_4B_SHA256` variables in the
`Makefile` are overridable.

| Field | Value |
| --- | --- |
| File | `Qwen3-Embedding-4B-Q8_0.gguf` |
| Size | 4 279 660 224 bytes (4.28 GB) |
| sha256 | `b60ae5ce2dd6a0b77f82cadf21def1f310a3e10cde380ad0081b07a9d416949d` |
| Quantization | Q8_0 (single file, no shards) |
| GGUF metadata | `general.architecture=qwen3`, `qwen3.pooling_type=3` (LAST), ctx 40960, dim 2560 |
| License | Apache-2.0 (Qwen team, Alibaba Group) |

Single-file GGUF, so `models/qwen3-embedding-4b/model.yaml` needs no `layout`/symlinks: the weight
is mounted by the `model-4b-q8-0-gguf` component at `$SNAP_COMPONENTS/model-4b-q8-0-gguf/` and
exposed as `MODEL_FILE`.

## Why this README is tracked

`snap/snapcraft.yaml` has a `local-component-files` part with `source: components`. Keeping this
directory in git makes a fresh clone buildable (and fails with a clear "file not found" instead of
a missing source directory) while the 4.28 GB weight stays out of the repository. The part
organizes only the `.gguf` into the component and prunes everything else, so this file is never
shipped inside the snap.
