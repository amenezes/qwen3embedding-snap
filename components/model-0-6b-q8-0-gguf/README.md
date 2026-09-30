# Qwen3-Embedding-0.6B-Q8_0.gguf

Model weights for [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), the
0.6B multilingual text embedding model from the Qwen team (Alibaba Group), quantized to Q8_0 by
the model authors and published in
[Qwen/Qwen3-Embedding-0.6B-GGUF](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF).

The official 0.6B GGUF repo publishes only Q8_0 and F16; Q8_0 is near-lossless at this scale
and roughly half the size of F16, which is why it is the default variant of this snap.

The weights are **not** committed (`.gitignore` excludes `*.gguf`). `make init` downloads them
into this directory and verifies the pinned checksum:

```shell
make download-models   # hf download $(GGUF_06B_REPO) $(GGUF_06B_FILE) --local-dir components/model-0-6b-q8-0-gguf
make verify-model      # sha256sum --check against GGUF_06B_SHA256 in the Makefile
```

To build offline (or from an internal mirror), place the file here yourself and run
`make verify-model`; the `GGUF_06B_REPO`/`GGUF_06B_FILE`/`GGUF_06B_SHA256` variables in the
`Makefile` are overridable.

| Field | Value |
| --- | --- |
| File | `Qwen3-Embedding-0.6B-Q8_0.gguf` |
| Size | 639 150 592 bytes (0.64 GB) |
| sha256 | `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439` |
| Quantization | Q8_0 (single file, no shards) |
| GGUF metadata | `general.architecture=qwen3`, `qwen3.pooling_type=3` (LAST), ctx 32768, dim 1024 |
| License | Apache-2.0 (Qwen team, Alibaba Group) |

Single-file GGUF, so `models/qwen3-embedding-0-6b/model.yaml` needs no `layout`/symlinks: the
weight is mounted by the `model-0-6b-q8-0-gguf` component at
`$SNAP_COMPONENTS/model-0-6b-q8-0-gguf/` and exposed as `MODEL_FILE`.

## Why this README is tracked

`snap/snapcraft.yaml` has a `local-component-files` part with `source: components`. Keeping this
directory in git makes a fresh clone buildable (and fails with a clear "file not found" instead of
a missing source directory) while the 0.64 GB weight stays out of the repository. The part
organizes only the `.gguf` into the component and prunes everything else, so this file is never
shipped inside the snap.
