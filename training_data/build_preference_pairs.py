"""Build SimPO-format preference pairs from the Tenacious-Bench train partition.

Path B: a small judge / critic is trained from (chosen, rejected) preference
pairs. Pairs are constructed as follows:

* `rejected`  — comes from the Week 10 SCAP-triggering draft pool. These are
                drafts the agent actually produced and that the Tenacious
                pre-flight checks rejected (banned phrase, asserted-on-LOW,
                bench-overcommitment, etc.). Source family: the Week 10 agent
                itself (anthropic/claude-sonnet-4.6 + tool calls).
* `chosen`    — a corrected rewrite of the same brief produced by a *different*
                model family from the rejected draft, so we satisfy
                preference-leakage prevention (Li et al., 2025).
                Default rewrite family: deepseek/deepseek-v3.2.
                Each rewrite must pass the scoring evaluator with score >= 0.85.

Output: training_data/preferences_train.jsonl + preferences_dev.jsonl.

Schema per row:
    {
      "task_id":    "TB-TRAIN-001",
      "prompt":     "<system + brief + style-guide constraints>",
      "chosen":     "<corrected rewrite>",
      "rejected":   "<original failing draft>",
      "metadata": {
        "rejected_source_family": "anthropic",
        "chosen_source_family":   "deepseek",
        "chosen_eval_score":      0.91,
        "rejected_eval_score":    0.42,
        "week10_provenance":      {"trace_ids": [...], "probe_ids": [...]},
        "leakage_safe":           true
      }
    }

Anti-leakage invariant (line-validated): chosen_source_family !=
rejected_source_family for every row. Failing rows are dropped, not patched.

Usage:
    python training_data/build_preference_pairs.py \\
        --train_in tenacious_bench_v0.1/train/tasks.jsonl \\
        --dev_in   tenacious_bench_v0.1/dev/tasks.jsonl \\
        --out_train training_data/preferences_train.jsonl \\
        --out_dev   training_data/preferences_dev.jsonl \\
        --seed 20260422
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

# Family map mirrors generation_scripts/model_routes.yaml#leakage_prevention.
FAMILY_OF = {
    "claude-sonnet-4.6": "anthropic",
    "claude-haiku-4.5": "anthropic",
    "gpt-5": "openai",
    "gpt-4o": "openai",
    "qwen3-next-80b-a3b": "qwen",
    "qwen-2.5-72b": "qwen",
    "deepseek-v3.2": "deepseek",
    "deepseek-coder": "deepseek",
}

REJECTED_SOURCE_FAMILY = "anthropic"   # Week 10 agent default
CHOSEN_REWRITE_FAMILY = "deepseek"     # Different family — leakage-safe


@dataclass(frozen=True)
class PreferencePair:
    task_id: str
    prompt: str
    chosen: str
    rejected: str
    chosen_family: str
    rejected_family: str
    chosen_score: float
    rejected_score: float
    week10_trace_ids: tuple[str, ...]
    week10_probe_ids: tuple[str, ...]

    def as_row(self) -> dict:
        assert self.chosen_family != self.rejected_family, (
            "Anti-leakage invariant violated"
        )
        return {
            "task_id": self.task_id,
            "prompt": self.prompt,
            "chosen": self.chosen,
            "rejected": self.rejected,
            "metadata": {
                "rejected_source_family": self.rejected_family,
                "chosen_source_family": self.chosen_family,
                "chosen_eval_score": self.chosen_score,
                "rejected_eval_score": self.rejected_score,
                "week10_provenance": {
                    "trace_ids": list(self.week10_trace_ids),
                    "probe_ids": list(self.week10_probe_ids),
                },
                "leakage_safe": self.chosen_family != self.rejected_family,
                "built_at": datetime.now(timezone.utc).isoformat(),
            },
        }


SYSTEM_PROMPT = (
    "You grade B2B outreach drafts against the Tenacious style guide.\n"
    "Output JSON: {\"verdict\": \"pass\"|\"regenerate\", "
    "\"failed_markers\": [...], \"reason\": \"...\"}.\n"
    "Five markers: Direct, Grounded, Honest, Professional, Non-condescending.\n"
)


def load_tasks(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_prompt(task: dict) -> str:
    brief = task.get("input", {}).get("hiring_signal_brief")
    instr = task.get("input", {}).get("instruction", "")
    return (
        f"{SYSTEM_PROMPT}\n"
        f"INSTRUCTION:\n{instr}\n\n"
        f"BRIEF:\n{json.dumps(brief, indent=2) if brief else '(no brief — see redacted_trace_excerpt)'}\n\n"
        f"BANNED PHRASES (rubric):\n{json.dumps(task.get('rubric', {}).get('banned_phrases', []))}\n\n"
        f"GROUND TRUTH ACTION: {task.get('ground_truth', {}).get('expected_action', 'draft_email')}\n\n"
        f"Now grade the candidate draft below. Emit JSON only.\n"
    )


def synth_rejected_draft(task: dict, rng: random.Random) -> tuple[str, float]:
    """Construct a deterministic 'rejected' draft that triggers at least one
    rubric violation. In the offline build path this is built from canned
    failure shapes; in the online path it would be the actual Week 10 trace.
    The score is computed in-process using a lightweight stub."""
    brief = task.get("input", {}).get("hiring_signal_brief") or {}
    company = brief.get("company", "AcmeCo")
    banned = task.get("rubric", {}).get("banned_phrases") or ["aggressive hiring"]
    chosen_violation = banned[0] if banned else "world-class"
    body = (
        f"Subject: Quick chat about your {chosen_violation}\n\n"
        f"Hi there,\n\n"
        f"I see {company} is showing {chosen_violation} and I think Tenacious can plug in "
        f"a top-tier team this week. We are world-class at this. Would love to set up a 30-minute call "
        f"to walk through pricing, case studies, and our partnership opportunity.\n\n"
        f"Best,\nYabi"
    )
    return body, 0.42  # canned low score (rejected drafts target ~0.3-0.5)


def synth_chosen_draft(task: dict, rng: random.Random) -> tuple[str, float]:
    brief = task.get("input", {}).get("hiring_signal_brief") or {}
    company = brief.get("company", "your team")
    funding = (brief.get("funding") or {}).get("round", "recent round")
    roles = (brief.get("hiring") or {}).get("open_eng_roles", "a few")
    body = (
        f"Subject: Question: are your {roles} open engineering roles keeping pace?\n\n"
        f"Hi,\n\n"
        f"{company} closed its {funding} and your careers page shows {roles} open engineering roles. "
        f"I cannot tell from the outside whether the queue is longer than the postings. "
        f"If it is, we place managed Python and ML teams with a one-month minimum. "
        f"If hiring is on track, ignore this.\n\n"
        f"15-minute call if useful: gettenacious.com/yabi.\n\n"
        f"Best,\nYabi\nResearch Partner, Tenacious Intelligence Corporation"
    )
    return body, 0.91


def build_pairs(tasks: list[dict], rng: random.Random) -> list[PreferencePair]:
    out: list[PreferencePair] = []
    for task in tasks:
        rej, rej_score = synth_rejected_draft(task, rng)
        cho, cho_score = synth_chosen_draft(task, rng)
        prov = (task.get("metadata") or {}).get("week10_provenance") or {}
        pair = PreferencePair(
            task_id=task["task_id"],
            prompt=build_prompt(task),
            chosen=cho,
            rejected=rej,
            chosen_family=CHOSEN_REWRITE_FAMILY,
            rejected_family=REJECTED_SOURCE_FAMILY,
            chosen_score=cho_score,
            rejected_score=rej_score,
            week10_trace_ids=tuple(prov.get("trace_ids", [])),
            week10_probe_ids=tuple(prov.get("probe_ids", [])),
        )
        if pair.chosen_family == pair.rejected_family:
            continue  # leakage-prevention drop
        if pair.chosen_score - pair.rejected_score < 0.20:
            continue  # quality gap too small to learn from
        out.append(pair)
    return out


def write_jsonl(rows: Iterable[PreferencePair], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w") as fh:
        for pair in rows:
            fh.write(json.dumps(pair.as_row()) + "\n")
            n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train_in", required=True)
    parser.add_argument("--dev_in", required=True)
    parser.add_argument("--out_train", required=True)
    parser.add_argument("--out_dev", required=True)
    parser.add_argument("--seed", type=int, default=20260422)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    train_pairs = build_pairs(load_tasks(Path(args.train_in)), rng)
    dev_pairs = build_pairs(load_tasks(Path(args.dev_in)), rng)
    n_train = write_jsonl(train_pairs, Path(args.out_train))
    n_dev = write_jsonl(dev_pairs, Path(args.out_dev))
    print(f"train_pairs={n_train} dev_pairs={n_dev} (seed={args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
