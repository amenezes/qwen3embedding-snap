#!/usr/bin/env python3
"""E2E test battery for the qwen3-embedding snap (OpenAI /v1/embeddings API).

Runs against any llama-server in embedding mode serving a Qwen3-Embedding
GGUF -- either the installed snap (default: port 8362) or a bare llama-server
started from the pinned runtime for pre-build validation.

Usage:
    python3 tests/embeddings-e2e.py [BASE_URL] [MODEL_NAME] [EXPECTED_DIM]

    BASE_URL      default http://127.0.0.1:8362
    MODEL_NAME    default qwen3-embedding-0-6b (the OpenAI model id / alias)
    EXPECTED_DIM  default 1024 (0.6B=1024, 4B=2560, 8B=4096)

Only the Python standard library is used, so it also runs inside minimal
environments (CI runners, containers) without setup.
"""
import json
import math
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8362"
MODEL = sys.argv[2] if len(sys.argv) > 2 else "qwen3-embedding-0-6b"
EXPECTED_DIM = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
results = []


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def embed(inputs, **extra):
    status, body = post("/v1/embeddings", {"model": MODEL, "input": inputs, **extra})
    if status != 200:
        raise AssertionError(f"HTTP {status}: {body}")
    vecs = [d["embedding"] for d in sorted(body["data"], key=lambda d: d["index"])]
    return vecs, body.get("usage")


def cos(a, b):
    return sum(x * y for x, y in zip(a, b)) / (
        math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b)))


def norm(a):
    return math.sqrt(sum(x * x for x in a))


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")


def server_ctx():
    """Context size the server was started with (from /v1/models meta)."""
    req = urllib.request.Request(BASE + "/v1/models")
    with urllib.request.urlopen(req, timeout=30) as r:
        meta = json.loads(r.read())["data"][0].get("meta", {})
    return int(meta.get("n_ctx", 0)) or None


def main():
    n_ctx = server_ctx()
    print(f"# server n_ctx={n_ctx}")
    # T1: basic shape + L2 normalization (llama-server --embd-normalize default 2).
    # Qwen3-Embedding vectors are meant to be L2-normalized so the dot product
    # equals cosine similarity.
    vecs, usage = embed("Hello world")
    v = vecs[0]
    check("T1 dim==expected", len(v) == EXPECTED_DIM, f"dim={len(v)}")
    check("T1 L2 norm==1.0", abs(norm(v) - 1.0) < 1e-3, f"|v|={norm(v):.6f}")
    check("T1 usage tokens reported", bool(usage) and usage.get("prompt_tokens", 0) > 0, str(usage))

    # T2: retrieval sanity with the official instruct format (model card):
    #     f"Instruct: {task}\nQuery: {query}" on the query side, documents raw.
    task = "Given a web search query, retrieve relevant passages that answer the query"
    q = f"Instruct: {task}\nQuery: What is the capital of China?"
    doc_pos = "The capital of China is Beijing."
    doc_neg = "Gravity is a force that attracts two bodies towards each other."
    (vq, vpos, vneg), _ = embed([q, doc_pos, doc_neg])
    s_pos, s_neg = cos(vq, vpos), cos(vq, vneg)
    check("T2 sim(query,pos) > sim(query,neg)", s_pos > s_neg, f"pos={s_pos:.4f} neg={s_neg:.4f}")
    check("T2 sim(query,pos) strong", s_pos > 0.5, f"pos={s_pos:.4f}")

    # T3: cross-lingual retrieval (pt-BR query, en document), instruction in
    # English as recommended by the vendor for multilingual use.
    q_pt = f"Instruct: {task}\nQuery: Qual é a capital do Brasil?"
    (v1, v2, v3), _ = embed([
        q_pt,
        "The capital of Brazil is Brasília.",
        "Water boils at 100 degrees Celsius at sea level.",
    ])
    check("T3 cross-lingual pt->en ordering", cos(v1, v2) > cos(v1, v3),
          f"pos={cos(v1, v2):.4f} neg={cos(v1, v3):.4f}")

    # T4: instruct helps (vendor claims 1-5% on most tasks): both forms must
    # order correctly; we record the margins as evidence.
    q_plain = "What is the capital of China?"
    (vp, vpl), _ = embed([q, q_plain])
    mi = cos(vq, vpos) - cos(vq, vneg)
    mq = cos(vpl, vpos) - cos(vpl, vneg)
    check("T4 instruct and plain both order correctly", mq > 0 and mi > 0,
          f"margin_instruct={mi:.4f} margin_plain={mq:.4f}")

    # T5: batch input, order preserved via the `index` field.
    texts = [f"document number {i} about topic {i * 7}" for i in range(8)]
    vb, ub = embed(texts)
    check("T5 batch size + dims", len(vb) == 8 and all(len(x) == EXPECTED_DIM for x in vb),
          f"n={len(vb)} tokens={ub.get('prompt_tokens') if ub else '?'}")

    # T6: MRL (Matryoshka) client-side truncation: keep the first N dims and
    # renormalize; ordering must be preserved (vendor-documented behavior).
    half = EXPECTED_DIM // 2
    trunc = lambda x: [t / norm(x[:half]) for t in x[:half]]
    tq, tp, tn = trunc(vq), trunc(vpos), trunc(vneg)
    check("T6 MRL@half ordering preserved", cos(tq, tp) > cos(tq, tn),
          f"pos={cos(tq, tp):.4f} neg={cos(tq, tn):.4f}")

    # T7 (informational): OpenAI `dimensions` request param. llama-server
    # b10344 accepts but ignores it (always returns the full dim), so MRL is
    # client-side. Recorded, not asserted, so a future runtime that implements
    # server-side truncation does not break the suite.
    status, body = post("/v1/embeddings", {"model": MODEL, "input": "test", "dimensions": 256})
    if status == 200 and isinstance(body, dict):
        d = len(body["data"][0]["embedding"])
        check("T7 dimensions param behavior recorded", True,
              f"accepted, returned dim={d} (server-side MRL: {d == 256})")
    else:
        check("T7 dimensions param behavior recorded", True,
              f"rejected HTTP {status} -> client-side MRL only: {str(body)[:120]}")

    # T8 (informational): llama-server keeps /v1/chat/completions reachable
    # even with --embedding; an embedding model outputs gibberish there.
    # Clients must use /v1/embeddings. Behavior recorded for the docs.
    status, body = post("/v1/chat/completions", {
        "model": MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 8})
    info = (body["choices"][0]["message"]["content"][:40].replace("\n", " ")
            if status == 200 and isinstance(body, dict) else str(body)[:80])
    check("T8 chat endpoint behavior recorded", True, f"HTTP {status}, output='{info}'")

    # T9a: long input that fits the server context (scaled to n_ctx so the
    # battery also passes against deliberately small test contexts).
    words = max(200, int((n_ctx or 8192) * 0.55 / 4))  # ~4 tokens/word
    long_text = " ".join(f"word{i}" for i in range(words))
    vl, ul = embed(long_text)
    check("T9a long input fits ctx", len(vl[0]) == EXPECTED_DIM,
          f"words={words} prompt_tokens={ul.get('prompt_tokens') if ul else '?'}")

    # T9b: over-context input is rejected with a clear HTTP 400
    # (exceed_context_size_error), not a crash or a silent truncation.
    huge_text = " ".join(f"token{i}" for i in range(max(9000, (n_ctx or 8192) * 3)))
    status, body = post("/v1/embeddings", {"model": MODEL, "input": huge_text})
    check("T9b over-context rejected with 400", status == 400 and "exceed" in str(body),
          f"HTTP {status}: {str(body)[:140]}")

    # T10: empty-string input edge case (must not crash the server).
    try:
        ve, _ = embed("")
        check("T10 empty input handled", len(ve[0]) == EXPECTED_DIM, f"dim={len(ve[0])}")
    except AssertionError as e:
        check("T10 empty input handled", True, f"rejected: {str(e)[:100]}")

    fails = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(fails)}/{len(results)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
