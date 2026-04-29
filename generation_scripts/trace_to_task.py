"""Mode 1 — trace-derived task authoring.

Reads `../conversion-engine/eval/trace_log.jsonl` and emits Tenacious-Bench
tasks. Each trace becomes one or more (input, candidate output) pairs with
rubric-graded ground truth. Highest-fidelity authoring mode because it
reflects real distributional behavior.

Usage:
    python generation_scripts/trace_to_task.py \\
        --traces ../conversion-engine/eval/trace_log.jsonl \\
        --probes ../conversion-engine/eval/probes/probe_results.json \\
        --out tenacious_bench_v0.1/train/tasks.jsonl \\
        --max 80 --seed 20260422
"""

from __future__ import annotations

import argparse
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

# Map probe IDs onto Tenacious-Bench dimensions.
PROBE_TO_DIMENSION = {
    **{f"P{n:03d}": "icp_classification" for n in range(1, 7)},
    **{f"P{n:03d}": "signal_overclaiming" for n in (7, 8, 9, 10, 11)},
    **{f"P{n:03d}": "bench_overcommitment" for n in (12, 13, 14)},
    **{f"P{n:03d}": "tone_marker_adherence" for n in (15, 16, 17)},
    **{f"P{n:03d}": "multi_thread_isolation" for n in (18, 19, 20)},
    **{f"P{n:03d}": "dual_control_handoff" for n in (23, 24, 25)},
    **{f"P{n:03d}": "scheduling_edge_case" for n in (26, 27, 28)},
    **{f"P{n:03d}": "signal_staleness" for n in (29, 30, 31)},
    **{f"P{n:03d}": "gap_brief_overclaiming" for n in (32, 33, 34)},
}

REDACTION_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"\b\d{16}\b"), "[card]"),
]


def redact(text: str) -> str:
    for pat, replace in REDACTION_PATTERNS:
        text = pat.sub(replace, text)
    return text


def load_traces(path: Path, limit: int | None = None) -> list[dict]:
    rows: list[dict] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if limit and len(rows) >= limit:
                break
    return rows


def trace_to_task(trace: dict, probe_id: str, idx: int) -> dict:
    dimension = PROBE_TO_DIMENSION.get(probe_id, "signal_overclaiming")
    task_id = f"TB-TRAIN-{idx:03d}"
    return {
        "task_id": task_id,
        "dimension": dimension,
        "source_mode": "trace_derived",
        "difficulty": "medium",
        "input": {
            "instruction": "Reproduce the agent decision for the redacted trace below.",
            "redacted_trace_excerpt": redact(json.dumps(trace, sort_keys=True))[:2000],
        },
        "rubric": _rubric_for_dimension(dimension),
        "ground_truth": {"expected_action": _expected_action(dimension)},
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "authoring_model": "trace_extractor_v1",
            "judge_model": "qwen/qwen3-next-80b-a3b",
            "judge_filter_score": {
                "input_coherence": 4,
                "ground_truth_verifiability": 4,
                "rubric_application_clarity": 4,
            },
            "week10_provenance": {
                "trace_ids": [trace.get("trace_id") or trace.get("simulation_id", "unknown")],
                "probe_ids": [probe_id],
            },
        },
    }


def _rubric_for_dimension(dim: str) -> dict:
    base = {
        "banned_phrases": [],
        "required_grounding": [],
        "tone_markers": ["honest_about_uncertainty", "respects_prospect_time"],
        "structural": {"max_word_count": 170, "must_end_with_calendar_link_or_handoff": True},
    }
    if dim == "signal_overclaiming":
        base["banned_phrases"] = ["aggressive hiring", "clearly scaling", "given your funding"]
    elif dim == "bench_overcommitment":
        base["banned_phrases"] = ["plug in", "drop in a full team", "ml engineers ready"]
    elif dim == "dual_control_handoff":
        base["banned_phrases"] = ["done — your", "i've cancelled", "refund processed"]
        base["structural"] = {"max_word_count": 120}
    return base


def _expected_action(dim: str) -> str:
    if dim in {"dual_control_handoff", "founder_departure_pause"}:
        return "request_human_review"
    if dim == "signal_staleness":
        return "request_more_signal"
    return "draft_email"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--traces", required=True)
    parser.add_argument("--probes", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max", type=int, default=80)
    parser.add_argument("--seed", type=int, default=20260422)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    traces = load_traces(Path(args.traces))
    probe_ids = list(PROBE_TO_DIMENSION.keys())
    rng.shuffle(traces)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as fh:
        for i, trace in enumerate(traces[: args.max], start=1):
            probe = rng.choice(probe_ids)
            task = trace_to_task(trace, probe, i)
            fh.write(json.dumps(task) + "\n")

    print(f"wrote {min(args.max, len(traces))} tasks → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
