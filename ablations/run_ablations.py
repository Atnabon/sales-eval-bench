"""Tenacious-Bench Path B ablation harness.

Implements all four challenge-spec ablations from a single parameterised
entrypoint.  Each ablation produces a row in ``ablation_results.json`` with a
point estimate, a 95 % bootstrap confidence interval, a paired-bootstrap
p-value, per-task scores, and the underlying held-out trace path.

* **Delta A** — trained judge gating the Week 10 generator vs. Week 10
  baseline alone.  Tested against the sealed Tenacious-Bench held-out
  partition.  Statistical test: paired bootstrap, 10 000 resamples, two-
  tailed p-value.  Must produce 95 % CI separation at p < 0.05 to be
  considered a positive lift.

* **Delta B** — trained judge gating the same backbone vs. a *prompt-
  engineered* version of the same intervention on the same backbone (no
  training).  Tests whether training actually beat what a careful prompt
  could do.  Same statistical machinery as Delta A.  A negative or null
  result here is a legitimate finding and is reported honestly per the
  challenge brief.

* **Delta C** — trained pipeline vs. Week 10 τ²-Bench retail score, *only
  if* the Week 10 score is on file.  Reuses the existing number; no
  re-running of τ²-Bench retail this week (cost-discipline rule).  Reported
  informationally.

* **Cost-Pareto** — per-task latency (ms), input tokens, output tokens,
  cost (USD) with and without the trained component, plus a 95 % CI on
  the cost delta.  Anchors the production recommendation.

The harness is deliberately runnable offline: when no judge model is
reachable it uses the deterministic offline scorer in
``evaluator/scoring_evaluator.py`` so the same code path is exercised in
CI and on Colab.

Usage:
    python ablations/run_ablations.py \\
        --held_out tenacious_bench_v0.1/held_out/tasks.jsonl \\
        --baseline_drafts ablations/data/baseline_drafts.jsonl \\
        --trained_drafts  ablations/data/trained_drafts.jsonl \\
        --prompted_drafts ablations/data/prompted_drafts.jsonl \\
        --t2_bench_score 0.7267 --t2_bench_ci 0.6504 0.7917 \\
        --out_dir ablations/output \\
        --seed 20260422

The four ``--*_drafts`` JSONL files each contain rows of shape:
    {"task_id": "TB-HOLD-001", "candidate": "...", "tokens_in": 1421,
     "tokens_out": 187, "latency_ms": 642, "cost_usd": 0.0034}
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import random
import statistics
import sys
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluator.scoring_evaluator import evaluate, load_task  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("ablations")


# ---------------------------------------------------------------------------
# Statistical primitives — paired bootstrap + percentile CI
# ---------------------------------------------------------------------------


def paired_bootstrap(
    a: list[float],
    b: list[float],
    n_resamples: int = 10_000,
    seed: int = 20260422,
) -> dict[str, float]:
    """Return point estimate, 95 % CI, and two-tailed paired-bootstrap
    p-value for the *delta* a - b. Inputs must be paired and same-length."""
    if len(a) != len(b):
        raise ValueError(f"paired_bootstrap requires same length, got {len(a)} vs {len(b)}")
    if not a:
        return {"delta": 0.0, "ci_low": 0.0, "ci_high": 0.0, "p_value": 1.0, "n": 0, "n_resamples": n_resamples}
    rng = random.Random(seed)
    diffs = [x - y for x, y in zip(a, b)]
    point = statistics.fmean(diffs)
    n = len(diffs)
    samples: list[float] = []
    for _ in range(n_resamples):
        boot = [diffs[rng.randrange(n)] for _ in range(n)]
        samples.append(statistics.fmean(boot))
    samples.sort()
    lo_idx = int(0.025 * n_resamples)
    hi_idx = int(0.975 * n_resamples)
    ci_low = samples[lo_idx]
    ci_high = samples[hi_idx]
    # Two-tailed p-value: fraction of bootstrap means with sign opposite to point.
    if point >= 0:
        tail = sum(1 for s in samples if s <= 0) / n_resamples
    else:
        tail = sum(1 for s in samples if s >= 0) / n_resamples
    p_value = min(1.0, 2.0 * tail)
    return {
        "delta": round(point, 4),
        "ci_low": round(ci_low, 4),
        "ci_high": round(ci_high, 4),
        "p_value": round(p_value, 4),
        "n": n,
        "n_resamples": n_resamples,
    }


def cost_delta_ci(per_task_costs_a: list[float], per_task_costs_b: list[float], seed: int) -> dict:
    """Bootstrap CI on the cost-per-task delta. Different from paired-bootstrap
    only in name — the math is identical."""
    return paired_bootstrap(per_task_costs_a, per_task_costs_b, seed=seed)


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DraftRecord:
    task_id: str
    candidate: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    cost_usd: float


@dataclass(frozen=True)
class DeltaRow:
    name: str
    description: str
    point_estimate: float
    ci_low: float
    ci_high: float
    p_value: float
    n: int
    n_resamples: int
    statistical_test: str
    direction: str
    holdout_traces_path: str
    extra: dict[str, Any]


def load_drafts(path: Path) -> dict[str, DraftRecord]:
    out: dict[str, DraftRecord] = {}
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            out[row["task_id"]] = DraftRecord(
                task_id=row["task_id"],
                candidate=row["candidate"],
                tokens_in=row.get("tokens_in", 0),
                tokens_out=row.get("tokens_out", 0),
                latency_ms=row.get("latency_ms", 0),
                cost_usd=row.get("cost_usd", 0.0),
            )
    return out


def score_drafts(
    held_out_path: Path,
    drafts: dict[str, DraftRecord],
    judge: str,
    traces_out: Path,
) -> tuple[list[float], list[dict]]:
    """Score every draft against its held-out task. Writes per-task scoring
    traces to traces_out as JSONL — these are the exact rows the demo video
    will open during the ablation segment."""
    scores: list[float] = []
    rows: list[dict] = []
    traces_out.parent.mkdir(parents=True, exist_ok=True)
    with held_out_path.open() as fh, traces_out.open("w") as out_fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            task = json.loads(line)
            tid = task["task_id"]
            if tid not in drafts:
                log.warning("missing draft for %s — skipping", tid)
                continue
            try:
                result = evaluate(task, drafts[tid].candidate, judge=judge)
            except Exception as exc:  # pragma: no cover — defensive
                log.error("scoring failure on %s: %s", tid, exc)
                log.error(traceback.format_exc())
                continue
            scores.append(result["score_total"])
            row = {
                "task_id": tid,
                "score": result["score_total"],
                "verdict": result["verdict"],
                "rubric_breakdown": result["rubric_breakdown"],
                "draft": drafts[tid].candidate[:600],  # truncated for readability
                "tokens_in": drafts[tid].tokens_in,
                "tokens_out": drafts[tid].tokens_out,
                "latency_ms": drafts[tid].latency_ms,
                "cost_usd": drafts[tid].cost_usd,
            }
            rows.append(row)
            out_fh.write(json.dumps(row) + "\n")
    return scores, rows


# ---------------------------------------------------------------------------
# Delta computations
# ---------------------------------------------------------------------------


def delta_a(
    baseline_scores: list[float],
    trained_scores: list[float],
    holdout_traces: Path,
    seed: int,
) -> DeltaRow:
    stats = paired_bootstrap(trained_scores, baseline_scores, seed=seed)
    direction = "positive" if stats["delta"] > 0 else ("null" if stats["delta"] == 0 else "negative")
    return DeltaRow(
        name="delta_A",
        description=(
            "Trained judge gating Week 10 generator vs. Week 10 baseline alone, "
            "Tenacious-Bench sealed held-out partition."
        ),
        point_estimate=stats["delta"],
        ci_low=stats["ci_low"],
        ci_high=stats["ci_high"],
        p_value=stats["p_value"],
        n=stats["n"],
        n_resamples=stats["n_resamples"],
        statistical_test="paired_bootstrap_two_tailed",
        direction=direction,
        holdout_traces_path=str(holdout_traces),
        extra={"baseline_mean": round(statistics.fmean(baseline_scores), 4) if baseline_scores else None,
               "trained_mean": round(statistics.fmean(trained_scores), 4) if trained_scores else None},
    )


def delta_b(
    prompted_scores: list[float],
    trained_scores: list[float],
    holdout_traces: Path,
    seed: int,
) -> DeltaRow:
    stats = paired_bootstrap(trained_scores, prompted_scores, seed=seed)
    direction = "positive" if stats["delta"] > 0 else ("null" if stats["delta"] == 0 else "negative")
    return DeltaRow(
        name="delta_B",
        description=(
            "Trained judge vs. prompt-engineered judge on the same backbone "
            "(no training), Tenacious-Bench held-out."
        ),
        point_estimate=stats["delta"],
        ci_low=stats["ci_low"],
        ci_high=stats["ci_high"],
        p_value=stats["p_value"],
        n=stats["n"],
        n_resamples=stats["n_resamples"],
        statistical_test="paired_bootstrap_two_tailed",
        direction=direction,
        holdout_traces_path=str(holdout_traces),
        extra={"prompted_mean": round(statistics.fmean(prompted_scores), 4) if prompted_scores else None,
               "trained_mean": round(statistics.fmean(trained_scores), 4) if trained_scores else None,
               "note": "Negative or null result is a legitimate finding per challenge brief."},
    )


def delta_c_informational(
    week10_t2_score: float | None,
    week10_t2_ci: tuple[float, float] | None,
    trained_t2_reused: bool,
) -> DeltaRow:
    """Delta C is informational only — challenge brief explicitly forbids
    re-running τ²-Bench retail this week. We reuse the Week 10 score if
    available; otherwise we record 'not applicable'."""
    if week10_t2_score is None:
        return DeltaRow(
            name="delta_C",
            description="τ²-Bench retail comparison (informational, not re-run).",
            point_estimate=float("nan"),
            ci_low=float("nan"),
            ci_high=float("nan"),
            p_value=float("nan"),
            n=0,
            n_resamples=0,
            statistical_test="not_applicable",
            direction="not_applicable",
            holdout_traces_path="",
            extra={"reason": "Week 10 τ²-Bench score not on file; informational only."},
        )
    return DeltaRow(
        name="delta_C",
        description=(
            "τ²-Bench retail Week 10 score (reused, not re-run). "
            "Tests whether the Tenacious-Bench lift is Tenacious-specific or general."
        ),
        point_estimate=week10_t2_score,
        ci_low=week10_t2_ci[0] if week10_t2_ci else float("nan"),
        ci_high=week10_t2_ci[1] if week10_t2_ci else float("nan"),
        p_value=float("nan"),
        n=150,  # standard τ²-Bench dev-slice size
        n_resamples=0,
        statistical_test="reused_week10_paired_bootstrap",
        direction="informational",
        holdout_traces_path="../conversion-engine/eval/baseline.md",
        extra={
            "rerun_this_week": False,
            "reused_from": "Week 10 baseline.md (cost-discipline rule)",
            "trained_t2_reused": trained_t2_reused,
        },
    )


def cost_pareto(
    baseline: dict[str, DraftRecord],
    trained: dict[str, DraftRecord],
    seed: int,
) -> dict[str, Any]:
    common = sorted(set(baseline) & set(trained))
    base_cost = [baseline[t].cost_usd for t in common]
    train_cost = [trained[t].cost_usd for t in common]
    base_lat = [baseline[t].latency_ms for t in common]
    train_lat = [trained[t].latency_ms for t in common]
    cost_d = cost_delta_ci(train_cost, base_cost, seed=seed)
    lat_d = paired_bootstrap([float(x) for x in train_lat],
                             [float(x) for x in base_lat], seed=seed)
    return {
        "n_paired_tasks": len(common),
        "cost_per_task_usd": {
            "baseline_mean": round(statistics.fmean(base_cost), 6) if base_cost else None,
            "trained_mean":  round(statistics.fmean(train_cost), 6) if train_cost else None,
            "delta_usd": cost_d["delta"],
            "ci_low":   cost_d["ci_low"],
            "ci_high":  cost_d["ci_high"],
            "p_value":  cost_d["p_value"],
        },
        "latency_ms_per_task": {
            "baseline_mean": round(statistics.fmean(base_lat), 2) if base_lat else None,
            "trained_mean":  round(statistics.fmean(train_lat), 2) if train_lat else None,
            "delta_ms": lat_d["delta"],
            "ci_low":   lat_d["ci_low"],
            "ci_high":  lat_d["ci_high"],
            "p_value":  lat_d["p_value"],
        },
    }


# ---------------------------------------------------------------------------
# Harness entrypoint
# ---------------------------------------------------------------------------


def run(
    held_out: Path,
    baseline_drafts_path: Path,
    trained_drafts_path: Path,
    prompted_drafts_path: Path,
    t2_score: float | None,
    t2_ci: tuple[float, float] | None,
    out_dir: Path,
    judge: str,
    seed: int,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)

    baseline = load_drafts(baseline_drafts_path)
    trained = load_drafts(trained_drafts_path)
    prompted = load_drafts(prompted_drafts_path)
    log.info("loaded baseline=%d trained=%d prompted=%d", len(baseline), len(trained), len(prompted))

    # Score each pool against the held-out partition. Per-task traces are
    # written to held_out_traces_*.jsonl so the demo video can open the rows
    # behind the headline numbers.
    base_scores, _ = score_drafts(
        held_out, baseline, judge,
        out_dir / "held_out_traces_baseline.jsonl",
    )
    trained_scores, _ = score_drafts(
        held_out, trained, judge,
        out_dir / "held_out_traces_trained.jsonl",
    )
    prompted_scores, _ = score_drafts(
        held_out, prompted, judge,
        out_dir / "held_out_traces_prompted.jsonl",
    )

    # Compute deltas. Defensive: short-circuit gracefully if any pool is empty.
    rows: list[DeltaRow] = []
    if base_scores and trained_scores:
        rows.append(delta_a(base_scores, trained_scores,
                            out_dir / "held_out_traces_trained.jsonl", seed))
    if prompted_scores and trained_scores:
        rows.append(delta_b(prompted_scores, trained_scores,
                            out_dir / "held_out_traces_trained.jsonl", seed))
    rows.append(delta_c_informational(t2_score, t2_ci, trained_t2_reused=True))

    pareto = cost_pareto(baseline, trained, seed=seed)

    report = {
        "schema_version": "v0.1",
        "seed": seed,
        "judge": judge,
        "deltas": [asdict(r) for r in rows],
        "cost_pareto": pareto,
        "n_held_out_tasks_scored": len(base_scores),
        "held_out_partition": str(held_out),
    }
    out_path = out_dir / "ablation_results.json"

    def _nan_to_null(o: Any) -> Any:
        if isinstance(o, float) and math.isnan(o):
            return None
        if isinstance(o, dict):
            return {k: _nan_to_null(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_nan_to_null(v) for v in o]
        return o

    out_path.write_text(json.dumps(_nan_to_null(report), indent=2) + "\n")
    log.info("wrote %s", out_path)

    summary = (
        ["# Ablation summary", ""]
        + [
            f"- **{r.name}** Δ={r.point_estimate:+.4f}  "
            f"(95 % CI [{r.ci_low:+.4f}, {r.ci_high:+.4f}], p={r.p_value:.4f}, n={r.n})  "
            f"[{r.direction}]"
            for r in rows
        ]
        + [
            "",
            f"- **Cost Δ/task** {pareto['cost_per_task_usd']['delta_usd']:+.6f} USD "
            f"(95 % CI [{pareto['cost_per_task_usd']['ci_low']:+.6f}, "
            f"{pareto['cost_per_task_usd']['ci_high']:+.6f}])",
            f"- **Latency Δ/task** {pareto['latency_ms_per_task']['delta_ms']:+.2f} ms "
            f"(95 % CI [{pareto['latency_ms_per_task']['ci_low']:+.2f}, "
            f"{pareto['latency_ms_per_task']['ci_high']:+.2f}])",
        ]
    )
    (out_dir / "ablation_summary.md").write_text("\n".join(summary) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--held_out", type=Path, required=True)
    parser.add_argument("--baseline_drafts", type=Path, required=True)
    parser.add_argument("--trained_drafts", type=Path, required=True)
    parser.add_argument("--prompted_drafts", type=Path, required=True)
    parser.add_argument("--t2_bench_score", type=float, default=None)
    parser.add_argument("--t2_bench_ci", type=float, nargs=2, default=None)
    parser.add_argument("--out_dir", type=Path, default=Path("ablations/output"))
    parser.add_argument("--judge", default="offline", choices=["offline", "dev", "eval"])
    parser.add_argument("--seed", type=int, default=20260422)
    args = parser.parse_args(argv)

    return run(
        held_out=args.held_out,
        baseline_drafts_path=args.baseline_drafts,
        trained_drafts_path=args.trained_drafts,
        prompted_drafts_path=args.prompted_drafts,
        t2_score=args.t2_bench_score,
        t2_ci=tuple(args.t2_bench_ci) if args.t2_bench_ci else None,
        out_dir=args.out_dir,
        judge=args.judge,
        seed=args.seed,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
