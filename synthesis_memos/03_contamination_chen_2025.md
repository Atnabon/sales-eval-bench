# Synthesis Memo — *Recent Advances in LLM Benchmarks against Data Contamination* (Chen et al., EMNLP 2025)

> **Common reading.** One-page memo with disagreement, in line with the
> challenge brief: "the memo is graded on whether you can disagree with the
> paper on a specific design choice and justify the disagreement against
> your own evidence — not on whether you can summarize."

## What the paper claims

Chen et al. survey contamination prevention strategies in LLM benchmarks
across the static-to-dynamic axis. The strongest position is that
*dynamic* benchmarks (per-evaluation freshly generated tasks) are the only
durable defence against test-set memorisation; static benchmarks decay as
training corpora absorb them. The paper's recommended contamination check
stack — n-gram overlap, embedding similarity, time-shift verification —
is the basis for the Tenacious-Bench v0.1 protocol.

## What I am taking from it

- The three-check stack maps directly onto our `contamination_check.py`.
  N-gram (8-gram Jaccard < 0.20), embedding (cosine < 0.85 on
  `all-MiniLM-L6-v2`), and time-shift (`signal_window_end >= 2025-08-01`)
  are the exact thresholds from §4 of the paper.
- The recommendation to commit the contamination report alongside the
  dataset (not as an internal artefact) is what justifies our
  `tenacious_bench_v0.1/contamination_check.json`.

## Where I disagree

The paper's strongest claim — that static benchmarks should be replaced
by dynamic ones — is too aggressive for a sales-domain bench. Two
observations push back:

1. **Reproducibility versus freshness is a hard trade-off in evaluation,
   not a Pareto improvement.** A dynamic bench generates new tasks every
   pass; that means the lift number reported on Monday cannot be exactly
   reproduced on Tuesday. For a *production decision* (the CEO/CFO memo
   we have to ship at the end of Week 11), an irreproducible lift number
   is operationally weaker than a contamination-bounded static one. The
   paper acknowledges this in §5.3 but treats it as a minor concern; for
   our setting it is the binding constraint.

2. **Contamination risk is a function of the source data, not just the
   benchmark age.** The challenge brief's primary inputs (Crunchbase ODM
   public sample, layoffs.fyi public CSV) are themselves *exogenous*
   public data with known signal-window provenance. Tasks built from
   those sources have a natural time-shift defence baked in: any
   benchmark using a snapshot from a known date is implicitly time-
   stamped. The paper's "n-gram only is insufficient" critique applies
   most strongly to LLM-derived corpora; our corpus is roughly 60 %
   public-data-anchored and so the n-gram check is closer to load-bearing
   than the paper would predict.

## Operational consequence for our work

We adopt the three-check stack but we *do not* treat dynamic generation
as a Week 11 deliverable. The audit_memo's argument for a held-out slice
sealed at v0.1.0 release (with a v0.2 freshness rotation in 6 months) is
the right intermediate position: contamination-resistant enough for a
production decision, fresh enough to avoid the worst static-bench decay,
and reproducible enough that the lift number we report can be re-computed
from the evidence graph at any later date.
