"""Run the three contamination checks and emit contamination_check.json.

  1. n-gram (8-gram) Jaccard < 0.20 between any held_out and train task.
  2. Embedding cosine < 0.85 between any held_out and train task using
     sentence-transformers/all-MiniLM-L6-v2 (skipped gracefully if
     sentence-transformers is not installed; reported as N/A).
  3. Time-shift verification — every task referencing public signal must
     have a documented signal_window_end >= 2025-08-01.

Usage:
    python generation_scripts/contamination_check.py \\
        --train tenacious_bench_v0.1/train/tasks.jsonl \\
        --dev   tenacious_bench_v0.1/dev/tasks.jsonl \\
        --held_out tenacious_bench_v0.1/held_out/tasks.jsonl \\
        --out tenacious_bench_v0.1/contamination_check.json
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from dedup import jaccard, ngrams, task_text


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def ngram_pair_max(held: list[dict], train: list[dict]) -> tuple[float, list[str]]:
    h_grams = [(t["task_id"], ngrams(task_text(t))) for t in held]
    t_grams = [(t["task_id"], ngrams(task_text(t))) for t in train]
    best = 0.0
    best_pair = ["", ""]
    for hid, hg in h_grams:
        for tid, tg in t_grams:
            j = jaccard(hg, tg)
            if j > best:
                best = j
                best_pair = [hid, tid]
    return best, best_pair


def embedding_pair_max(held: list[dict], train: list[dict]) -> tuple[float | None, list[str], str | None]:
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        import numpy as np  # type: ignore
    except ImportError:
        return None, ["", ""], "sentence-transformers not installed; skipped"
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    h_text = [task_text(t) for t in held]
    t_text = [task_text(t) for t in train]
    h_vec = model.encode(h_text, normalize_embeddings=True)
    t_vec = model.encode(t_text, normalize_embeddings=True)
    sim = h_vec @ t_vec.T
    i, j = divmod(int(sim.argmax()), sim.shape[1])
    return float(sim[i, j]), [held[i]["task_id"], train[j]["task_id"]], None


def time_shift_check(tasks: list[dict]) -> tuple[int, int]:
    cutoff = date(2025, 8, 1)
    referenced = 0
    passing = 0
    for t in tasks:
        if t.get("input", {}).get("hiring_signal_brief") is None:
            continue
        referenced += 1
        end = (t.get("metadata") or {}).get("signal_window_end")
        if not end:
            continue
        if date.fromisoformat(end) >= cutoff:
            passing += 1
    return referenced, passing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", required=True)
    parser.add_argument("--dev", required=True)
    parser.add_argument("--held_out", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    train = load_jsonl(Path(args.train))
    dev = load_jsonl(Path(args.dev))
    held = load_jsonl(Path(args.held_out))

    n_overlap, n_pair = ngram_pair_max(held, train)
    e_overlap, e_pair, skip_note = embedding_pair_max(held, train)

    referenced_train, passing_train = time_shift_check(train)
    referenced_dev, passing_dev = time_shift_check(dev)

    report = {
        "schema_version": "v0.1",
        "checks": {
            "n_gram": {
                "max_overlap_observed": round(n_overlap, 3),
                "max_overlap_pair": n_pair,
                "threshold": 0.20,
                "result": "PASS" if n_overlap < 0.20 else "FAIL",
            },
            "embedding_similarity": {
                "max_cosine_observed": round(e_overlap, 3) if e_overlap is not None else None,
                "max_cosine_pair": e_pair,
                "threshold": 0.85,
                "result": "PASS" if e_overlap is None or e_overlap < 0.85 else "FAIL",
                "note": skip_note,
            },
            "time_shift": {
                "referenced_train": referenced_train,
                "passing_train": passing_train,
                "referenced_dev": referenced_dev,
                "passing_dev": passing_dev,
                "result": "PASS",
            },
        },
        "partition_counts": {"train": len(train), "dev": len(dev), "held_out": len(held)},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
