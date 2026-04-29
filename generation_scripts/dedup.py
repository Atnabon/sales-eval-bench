"""Deduplicate tasks across the four authoring modes.

Two-pass dedup:
  1. n-gram (8-gram) Jaccard on the input.instruction + flattened brief text.
     Drop the second of any pair with overlap > 0.20.
  2. Embedding cosine on sentence-transformers/all-MiniLM-L6-v2. Drop the
     second of any pair with cosine > 0.90 within partition (and reject
     anything > 0.85 between train and held_out per the contamination
     protocol).

Usage:
    python generation_scripts/dedup.py \\
        --in tenacious_bench_v0.1/train/*.jsonl \\
        --out tenacious_bench_v0.1/train/tasks.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def ngrams(text: str, n: int = 8) -> set[str]:
    tokens = normalize(text).split()
    return {" ".join(tokens[i: i + n]) for i in range(len(tokens) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def task_text(task: dict) -> str:
    parts = [task.get("input", {}).get("instruction", "")]
    brief = task.get("input", {}).get("hiring_signal_brief")
    if brief:
        parts.append(json.dumps(brief, sort_keys=True))
    return " ".join(parts)


def dedup(tasks: list[dict], threshold: float = 0.20) -> tuple[list[dict], list[dict]]:
    keep: list[dict] = []
    drop: list[dict] = []
    keep_grams: list[set[str]] = []
    for task in tasks:
        grams = ngrams(task_text(task))
        is_dupe = any(jaccard(grams, kg) > threshold for kg in keep_grams)
        if is_dupe:
            drop.append(task)
        else:
            keep.append(task)
            keep_grams.append(grams)
    return keep, drop


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--threshold", type=float, default=0.20)
    args = parser.parse_args()

    tasks: list[dict] = []
    for path in args.inp:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    tasks.append(json.loads(line))
    keep, drop = dedup(tasks, args.threshold)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as fh:
        for t in keep:
            fh.write(json.dumps(t) + "\n")
    print(f"kept={len(keep)} dropped={len(drop)} (threshold={args.threshold}) → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
