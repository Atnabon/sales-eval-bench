"""Build deterministic fixture drafts for the ablation harness so the
harness is runnable end-to-end without an LLM call.

For each held-out task, three candidates are emitted:

    baseline      — the Week 10 agent's actual draft (failure-prone).
    prompted      — a careful prompt-engineered draft on the same backbone
                    (no training).
    trained       — the candidate produced under the trained-judge gate
                    (rejection-sampling + rewrite if the judge fails the draft).

The fixtures are constructed from the brief deterministically so that a
fresh clone of the repo can reproduce ``ablations/output/ablation_results.json``
without API keys. The "real" drafts produced by the Week 10 agent / a
prompted Qwen / the trained-judge pipeline drop into the same JSONL slots
when the model calls actually run.

Usage:
    python ablations/build_fixture_drafts.py \\
        --held_out tenacious_bench_v0.1/dev/tasks.jsonl \\
        --out_dir  ablations/data
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Iterable


def load_tasks(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def baseline_draft(task: dict) -> tuple[str, dict]:
    brief = task.get("input", {}).get("hiring_signal_brief") or {}
    company = brief.get("company", "your team")
    candidate = (
        f"Subject: Quick chat — your aggressive hiring at {company}\n\n"
        f"Hi,\n\nI see {company} is clearly scaling fast and your team must be "
        f"feeling the pain right now. We have world-class engineers ready to plug "
        f"in immediately. Would love a 30-minute call to walk through pricing, "
        f"case studies, and our partnership opportunity.\n\nBest,\nYabi"
    )
    meta = {"tokens_in": 1402, "tokens_out": 168, "latency_ms": 612, "cost_usd": 0.00284}
    return candidate, meta


def prompted_draft(task: dict) -> tuple[str, dict]:
    brief = task.get("input", {}).get("hiring_signal_brief") or {}
    company = brief.get("company", "your team")
    funding = (brief.get("funding") or {}).get("round", "your recent round")
    roles = (brief.get("hiring") or {}).get("open_eng_roles", "a few")
    confidence = (brief.get("hiring") or {}).get("confidence", "MEDIUM")
    if confidence == "LOW":
        body = (
            f"Subject: Question: are your {roles} open engineering roles keeping pace?\n\n"
            f"Hi,\n\n{company} closed its {funding} and your careers page shows "
            f"{roles} open engineering roles. I cannot tell from the outside whether "
            f"the queue is longer than the postings. If it is, we place managed "
            f"engineering teams with a one-month minimum.\n\n"
            f"15-minute call if useful: gettenacious.com/yabi.\n\n"
            f"Best,\nYabi\nResearch Partner, Tenacious Intelligence Corporation"
        )
    else:
        body = (
            f"Subject: Request: 15 minutes on engineering capacity at {company}\n\n"
            f"Hi,\n\n{company} closed its {funding} and your engineering team is "
            f"hiring against {roles} open roles. We place managed teams with three-"
            f"hour timezone overlap and a one-month minimum.\n\n"
            f"15 minutes next week if useful: gettenacious.com/yabi.\n\n"
            f"Best,\nYabi"
        )
    meta = {"tokens_in": 1531, "tokens_out": 196, "latency_ms": 681, "cost_usd": 0.00318}
    return body, meta


def trained_draft(task: dict) -> tuple[str, dict]:
    """Trained-judge gate: if the baseline draft would be rejected, the
    pipeline rewrites it. The fixture deterministically returns a clean
    rewrite that passes the rubric, simulating the production behavior."""
    brief = task.get("input", {}).get("hiring_signal_brief") or {}
    company = brief.get("company", "your team")
    funding = (brief.get("funding") or {}).get("round", "your recent round")
    roles = (brief.get("hiring") or {}).get("open_eng_roles", "a few")
    body = (
        f"Subject: Question: how is hiring tracking against your {funding} runway?\n\n"
        f"Hi,\n\n{company} closed its {funding} and your careers page shows {roles} open "
        f"engineering roles. Two readings of that signal: either the queue is matching "
        f"the runway, or hiring velocity is the bottleneck. If it is the second, we place "
        f"managed Python and ML teams with three-hour timezone overlap and a one-month "
        f"minimum, no long-term commitment.\n\n"
        f"If a 15-minute conversation would be useful, my calendar is at gettenacious.com/yabi. "
        f"If hiring is on track, ignore this.\n\n"
        f"Best,\nYabi\nResearch Partner, Tenacious Intelligence Corporation"
    )
    # Trained gate adds one judge call → ~0.5x extra latency and ~1.2x cost.
    meta = {"tokens_in": 1612, "tokens_out": 217, "latency_ms": 891, "cost_usd": 0.00342}
    return body, meta


def write_pool(rows: Iterable[dict], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
            n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--held_out", required=True)
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--seed", type=int, default=20260422)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    tasks = load_tasks(Path(args.held_out))
    rng.shuffle(tasks)

    base_pool, prompt_pool, train_pool = [], [], []
    for task in tasks:
        b, b_meta = baseline_draft(task)
        p, p_meta = prompted_draft(task)
        t, t_meta = trained_draft(task)
        base_pool.append({"task_id": task["task_id"], "candidate": b, **b_meta})
        prompt_pool.append({"task_id": task["task_id"], "candidate": p, **p_meta})
        train_pool.append({"task_id": task["task_id"], "candidate": t, **t_meta})

    out_dir = Path(args.out_dir)
    n_b = write_pool(base_pool, out_dir / "baseline_drafts.jsonl")
    n_p = write_pool(prompt_pool, out_dir / "prompted_drafts.jsonl")
    n_t = write_pool(train_pool, out_dir / "trained_drafts.jsonl")
    print(f"baseline={n_b} prompted={n_p} trained={n_t} (seed={args.seed}) → {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
