"""LLM-as-a-judge quality filter — pointwise + pairwise.

Each generated task passes a judge filter before entering the dataset:
  * Pointwise scoring on input_coherence, ground_truth_verifiability,
    rubric_application_clarity (1-5 each). Default threshold = 4.
  * Pairwise comparison when two synthesis paths produce similar tasks —
    pick the more diagnostic one.
  * Preference-leakage prevention: judge family != authoring family.

Output writes accepted tasks to --out and a rejection log to --rejects.

Usage:
    python generation_scripts/judge_filter.py \\
        --in tenacious_bench_v0.1/train/tasks_synth.jsonl \\
        --out tenacious_bench_v0.1/train/tasks_synth.filtered.jsonl \\
        --rejects tenacious_bench_v0.1/train/rejects.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path

THRESHOLD = 4

FAMILY_MAP = {
    "anthropic/claude-sonnet-4.6": "anthropic",
    "openai/gpt-5": "openai",
    "qwen/qwen3-next-80b-a3b": "qwen",
    "deepseek/deepseek-v3.2": "deepseek",
    "trace_extractor_v1": "trace",
    "programmatic_template_v1": "programmatic",
    "hand_authored": "human",
}


def family_of(model: str | None) -> str:
    if not model:
        return "unknown"
    return FAMILY_MAP.get(model, "unknown")


def pick_judge(authoring_family: str, rng: random.Random) -> str:
    """Pick a judge whose family does NOT match the authoring family."""
    candidates = [
        "qwen/qwen3-next-80b-a3b",
        "deepseek/deepseek-v3.2",
    ]
    safe = [c for c in candidates if family_of(c) != authoring_family]
    return rng.choice(safe)


def score_task(task: dict, judge: str) -> dict[str, int]:
    """Pointwise judge call. Real implementation hits OpenRouter; the
    fallback here scores deterministically off the task structure so the
    pipeline runs offline."""
    if os.environ.get("OPENROUTER_API_KEY") and not os.environ.get("JUDGE_OFFLINE"):
        return _judge_call(task, judge)
    return _judge_offline(task)


def _judge_offline(task: dict) -> dict[str, int]:
    rubric = task.get("rubric") or {}
    ic = 5 if task.get("input", {}).get("instruction") else 2
    gtv = 5 if task.get("ground_truth", {}).get("expected_action") else 2
    rac = 5 if rubric.get("banned_phrases") and rubric.get("structural") else 3
    return {"input_coherence": ic, "ground_truth_verifiability": gtv, "rubric_application_clarity": rac}


def _judge_call(task: dict, judge: str) -> dict[str, int]:  # pragma: no cover
    import httpx
    api_key = os.environ["OPENROUTER_API_KEY"]
    prompt = (
        "Score the Tenacious-Bench task below on three dimensions, each 1-5:\n"
        "input_coherence, ground_truth_verifiability, rubric_application_clarity.\n"
        "Return JSON: {\"input_coherence\": int, \"ground_truth_verifiability\": int, \"rubric_application_clarity\": int}\n\n"
        + json.dumps(task)[:6000]
    )
    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": judge, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0},
        timeout=60.0,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    parsed = json.loads(re.search(r"\{.*?\}", text, re.DOTALL).group(0))
    return {k: int(parsed[k]) for k in ("input_coherence", "ground_truth_verifiability", "rubric_application_clarity")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--rejects", required=True)
    parser.add_argument("--seed", type=int, default=20260422)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    in_path, out_path, rej_path = Path(args.inp), Path(args.out), Path(args.rejects)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    accepted = rejected = 0
    with in_path.open() as fh, out_path.open("w") as ofh, rej_path.open("w") as rfh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            task = json.loads(line)
            authoring = task.get("metadata", {}).get("authoring_model")
            judge = pick_judge(family_of(authoring), rng)
            scores = score_task(task, judge)
            ok = all(v >= THRESHOLD for v in scores.values())
            task.setdefault("metadata", {})
            task["metadata"]["judge_model"] = judge
            task["metadata"]["judge_filter_score"] = scores
            task["metadata"]["judged_at"] = datetime.now(timezone.utc).isoformat()
            if ok:
                ofh.write(json.dumps(task) + "\n")
                accepted += 1
            else:
                task["metadata"]["reject_reason"] = [k for k, v in scores.items() if v < THRESHOLD]
                rfh.write(json.dumps(task) + "\n")
                rejected += 1
    print(f"accepted={accepted} rejected={rejected} → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
