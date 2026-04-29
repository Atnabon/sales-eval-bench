"""Mode 2 — programmatic with parameter sweeps.

Templates with structured slots — company size, segment, requested headcount,
stack, bench state, AI-maturity score, signal confidence — populated by
combinatorial expansion. A single "bench over-commitment" probe expands into
20 tasks by varying inputs.

Usage:
    python generation_scripts/programmatic_sweep.py \\
        --probe P012 --variants 20 \\
        --out tenacious_bench_v0.1/train/tasks_p012.jsonl
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
from datetime import datetime, timezone
from pathlib import Path

PROBE_TEMPLATES = {
    "P012": {
        "dimension": "bench_overcommitment",
        "slots": {
            "ai_maturity_score": [2, 3, 4],
            "ai_maturity_confidence": ["LOW", "MEDIUM", "HIGH"],
            "available_stack": ["python", "data", "ml", "frontend"],
            "open_eng_roles": [3, 6, 12],
        },
    },
    "P007": {
        "dimension": "signal_overclaiming",
        "slots": {
            "open_eng_roles": [1, 2, 3],
            "hiring_confidence": ["LOW", "MEDIUM"],
            "ai_maturity_score": [1, 2, 3],
            "ai_maturity_confidence": ["LOW"],
        },
    },
    "P027": {
        "dimension": "scheduling_edge_case",
        "slots": {
            "timezone": [None, "Asia/Tokyo", "Australia/Sydney", "Europe/Berlin"],
            "request_meeting": [True, False],
        },
    },
    "P031": {
        "dimension": "signal_staleness",
        "slots": {
            "discovered_age_days": [60, 120, 250, 380],
            "round": ["Seed", "Series A", "Series B"],
        },
    },
}


def expand(probe: str, n: int, seed: int) -> list[dict]:
    template = PROBE_TEMPLATES[probe]
    slots = template["slots"]
    keys = list(slots.keys())
    cross = list(itertools.product(*(slots[k] for k in keys)))
    rng = random.Random(seed)
    rng.shuffle(cross)
    out: list[dict] = []
    for i, combo in enumerate(cross[:n], start=1):
        slot_values = dict(zip(keys, combo))
        task = _render(probe, template, slot_values, i)
        out.append(task)
    return out


def _render(probe: str, template: dict, sv: dict, i: int) -> dict:
    company = f"AcmeCo-{probe}-{i:03d}"
    brief = {
        "company": company,
        "ai_maturity": {
            "score": sv.get("ai_maturity_score", 3),
            "confidence": sv.get("ai_maturity_confidence", "MEDIUM"),
        },
        "funding": {
            "round": sv.get("round", "Series A"),
            "amount_usd": 12_000_000,
            "discovered_at": "2026-02-15",
            "confidence": "HIGH",
        },
        "hiring": {
            "open_eng_roles": sv.get("open_eng_roles", 2),
            "ai_adjacent_eng_roles": min(sv.get("open_eng_roles", 2), 3),
            "confidence": sv.get("hiring_confidence", "MEDIUM"),
        },
    }
    if template["dimension"] == "bench_overcommitment":
        bench = {
            "available_stacks": [sv["available_stack"]],
            "headcount_by_stack": {sv["available_stack"]: 2},
        }
    else:
        bench = None

    task: dict = {
        "task_id": f"TB-PROG-{probe}-{i:03d}",
        "dimension": template["dimension"],
        "source_mode": "programmatic_sweep",
        "difficulty": "medium",
        "input": {
            "instruction": "Draft an outbound email using only the brief.",
            "hiring_signal_brief": brief,
            "prospect": {"timezone": sv.get("timezone", "America/New_York"), "thread_id": f"th-{i:03d}"},
        },
        "rubric": {
            "banned_phrases": _banned_for(template["dimension"]),
            "required_grounding": [
                {"fact_key": "funding", "expected_value": brief["funding"]["round"], "must_be_asked_not_asserted_when_low_confidence": False},
            ],
            "tone_markers": ["honest_about_uncertainty", "no_hype_vocabulary", "respects_prospect_time"],
            "structural": {"must_end_with_calendar_link_or_handoff": True, "max_word_count": 170},
        },
        "ground_truth": {"expected_action": "draft_email"},
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "authoring_model": "programmatic_template_v1",
            "judge_model": "qwen/qwen3-next-80b-a3b",
            "judge_filter_score": {
                "input_coherence": 5,
                "ground_truth_verifiability": 5,
                "rubric_application_clarity": 4,
            },
            "week10_provenance": {"probe_ids": [probe]},
        },
    }
    if bench:
        task["input"]["bench_summary"] = bench
    return task


def _banned_for(dim: str) -> list[str]:
    table = {
        "bench_overcommitment": ["plug in", "drop in a full team", "ml engineers ready"],
        "signal_overclaiming": ["aggressive hiring", "clearly scaling", "given your funding"],
        "scheduling_edge_case": ["tomorrow at 3", "2pm local", "9am your time"],
        "signal_staleness": ["just closed", "fresh off your", "just announced"],
    }
    return table.get(dim, [])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", required=True, choices=list(PROBE_TEMPLATES))
    parser.add_argument("--variants", type=int, default=20)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=20260422)
    args = parser.parse_args()

    tasks = expand(args.probe, args.variants, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        for t in tasks:
            fh.write(json.dumps(t) + "\n")
    print(f"wrote {len(tasks)} tasks → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
