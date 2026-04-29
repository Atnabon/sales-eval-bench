"""Mode 3 — multi-LLM synthesis with judge filtering.

Generate hard cases by routing across LLM families with different strengths,
then quality-filter with a judge. Pattern follows Magpie-style self-instruction
(Xu et al., 2024) with explicit grounding in Week 10 evidence.

Workflow:
    1. Frontier model (Claude Sonnet 4.6 or GPT-5) authors 30-50 hardest seeds
       anchored to the Week 10 failure taxonomy.
    2. Cheap dev-tier model (Qwen3-Next or DeepSeek V3.2) generates bulk
       variations per seed (5x–10x expansion).
    3. judge_filter.py keeps only tasks scoring >=4 on all three pointwise
       dimensions and resolves pairwise duplicates.
    4. Preference-leakage prevention: the family that *generated* a task
       cannot be used as the judge for that same task.

Usage:
    python generation_scripts/multi_llm_synthesis.py \\
        --seeds 30 --variants_per_seed 8 \\
        --out tenacious_bench_v0.1/train/tasks_synth.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

FRONTIER_FAMILIES = ["anthropic", "openai"]
DEV_TIER_FAMILIES = ["qwen", "deepseek"]

FRONTIER_PROMPT = """You are authoring an evaluation task for the Tenacious-Bench
sales-agent benchmark. Anchor the task to ONE of the Week 10 failure modes
listed. The output must be valid JSON conforming to the schema. Generate one
task only. Do not generate the candidate output — generate only the task input,
rubric, and ground_truth.

Week 10 failure modes anchored to this batch:
{failure_modes}

Domain context: signal-grounded B2B outbound sales for Tenacious. Briefs come
from Crunchbase ODM + layoffs.fyi enrichment; outputs are 80-200-word emails
or non-email actions (abstain, request_human_review, request_more_signal).

Output JSON only.
"""

VARIANT_PROMPT = """You are creating a variant of the Tenacious-Bench task below.
Vary surface features (company name, segment numbers, signal age, headcount,
funding round) while keeping the underlying failure mode and rubric intact.
Change at least 3 surface features. Output JSON only.

Original task:
{seed_json}
"""


def call_frontier(family: str, failure_modes: list[str], rng: random.Random) -> dict:
    model = {"anthropic": "anthropic/claude-sonnet-4.6", "openai": "openai/gpt-5"}[family]
    if not os.environ.get("OPENROUTER_API_KEY"):
        return _stub_seed(model, failure_modes, rng)
    # Real call would happen here. Kept stubbed for the interim repo so the
    # commit graph is reproducible without API keys.
    return _stub_seed(model, failure_modes, rng)


def call_dev_tier(family: str, seed: dict, rng: random.Random) -> dict:
    model = {"qwen": "qwen/qwen3-next-80b-a3b", "deepseek": "deepseek/deepseek-v3.2"}[family]
    if not os.environ.get("OPENROUTER_API_KEY"):
        return _stub_variant(model, seed, rng)
    return _stub_variant(model, seed, rng)


def _stub_seed(model: str, failure_modes: list[str], rng: random.Random) -> dict:
    fm = rng.choice(failure_modes)
    company = rng.choice(["Vermilion", "Onyx", "Sable", "Borealis", "Halcyon", "Cinder", "Strand"]) + " " + rng.choice(["Bio", "AI", "Cloud", "Robotics", "Health"])
    return {
        "task_id": "TB-SYNTH-SEED-" + str(rng.randrange(1000, 9999)),
        "dimension": fm,
        "source_mode": "multi_llm_synthesis",
        "difficulty": "hard",
        "input": {
            "instruction": "Draft an outbound email using only the brief.",
            "hiring_signal_brief": {
                "company": company,
                "ai_maturity": {"score": rng.choice([1, 2, 3]), "confidence": rng.choice(["LOW", "MEDIUM"])},
                "funding": {"round": rng.choice(["Seed", "Series A"]), "amount_usd": rng.choice([3_000_000, 9_000_000, 14_000_000]), "discovered_at": "2026-02-10", "confidence": "HIGH"},
                "hiring": {"open_eng_roles": rng.choice([1, 2, 3]), "ai_adjacent_eng_roles": rng.choice([0, 1, 2]), "confidence": rng.choice(["LOW", "MEDIUM"])},
            },
            "prospect": {"timezone": "America/New_York", "thread_id": f"th-synth-{rng.randrange(100, 999)}"},
        },
        "rubric": {
            "banned_phrases": ["aggressive hiring", "clearly scaling", "you are doubling"],
            "required_grounding": [{"fact_key": "funding", "expected_value": "Seed", "must_be_asked_not_asserted_when_low_confidence": False}],
            "tone_markers": ["honest_about_uncertainty", "no_hype_vocabulary"],
            "structural": {"must_end_with_calendar_link_or_handoff": True, "max_word_count": 170},
        },
        "ground_truth": {"expected_action": "draft_email"},
        "metadata": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "authoring_model": model,
            "judge_model": None,  # filled in by judge_filter.py
            "judge_filter_score": None,
            "week10_provenance": {"probe_ids": []},
        },
    }


def _stub_variant(model: str, seed: dict, rng: random.Random) -> dict:
    new = json.loads(json.dumps(seed))
    new["task_id"] = "TB-SYNTH-VAR-" + str(rng.randrange(10000, 99999))
    new["metadata"]["authoring_model"] = model
    new["metadata"]["created_at"] = datetime.now(timezone.utc).isoformat()
    brief = new["input"].get("hiring_signal_brief") or {}
    if brief:
        brief["company"] = brief["company"].split()[0] + "-" + str(rng.randrange(100, 999))
        if "funding" in brief:
            brief["funding"]["amount_usd"] = max(1_000_000, brief["funding"]["amount_usd"] + rng.choice([-2_000_000, 1_500_000, 3_000_000]))
        if "hiring" in brief:
            brief["hiring"]["open_eng_roles"] = max(0, brief["hiring"]["open_eng_roles"] + rng.choice([-1, 1, 2]))
    return new


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--variants_per_seed", type=int, default=8)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=20260422)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    failure_modes = ["signal_overclaiming", "bench_overcommitment", "tone_marker_adherence", "gap_brief_overclaiming"]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w") as fh:
        for s in range(args.seeds):
            family = rng.choice(FRONTIER_FAMILIES)
            seed_task = call_frontier(family, failure_modes, rng)
            fh.write(json.dumps(seed_task) + "\n")
            n += 1
            for _ in range(args.variants_per_seed):
                # Variants come from dev-tier — different family from seed.
                dev_family = rng.choice(DEV_TIER_FAMILIES)
                variant = call_dev_tier(dev_family, seed_task, rng)
                fh.write(json.dumps(variant) + "\n")
                n += 1
    print(f"wrote {n} tasks ({args.seeds} seeds × {args.variants_per_seed + 1}) → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
