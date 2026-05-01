# Synthesis Memo — *A Survey on LLM-as-a-Judge* (Gu et al., 2024–2025)

> **Common reading.** One-page memo. Required for the dataset authoring
> path because every generated task in Tenacious-Bench passes through
> the LLM-judge filter pipeline before entering the dataset.

## What the paper claims

Gu et al. survey the landscape of LLM-as-a-judge: pointwise scoring,
pairwise ranking, list-wise ranking, judge-of-judges, jury voting. The
paper's three operational recommendations are:

1. **Compositional rubrics.** A judge graded on three to five orthogonal
   dimensions (rather than one aggregate "is this good?") is more reliable
   and easier to debug.
2. **Family separation between author and judge.** Especially critical
   when training data is synthesised; otherwise the same model's biases
   are reinforced through both sides of the loop. (This is the
   downstream subject of Li et al. 2025 Preference Leakage.)
3. **Tier separation in production.** A cheap dev-tier judge for high-
   volume filtering during dataset authoring, with an eval-tier judge
   reserved for the sealed held-out only.

## What I am taking from it

All three recommendations land directly in our pipeline:

- `evaluator/scoring_evaluator.py` and `generation_scripts/judge_filter.py`
  both use compositional rubrics — the evaluator scores 4 components, the
  filter scores 3 dimensions. Threshold is documented per dimension.
- `generation_scripts/model_routes.yaml` enforces family separation.
  `pick_judge` in `judge_filter.py` will not route a Qwen-authored task to
  a Qwen judge.
- `--judge eval` in the scoring evaluator only routes to Claude Sonnet 4.6
  for the sealed slice on Day 6. Days 2–3 iteration uses `--judge dev`
  exclusively, per the cost-discipline rule in the challenge brief.

## Where I disagree

The paper recommends jury voting (3+ judges, majority) as the gold
standard for high-stakes evaluations. For Tenacious-Bench v0.1 I think
this is the wrong trade-off:

1. **Cost.** Jury voting at the eval-tier triples the per-task cost of
   the sealed held-out pass. With our $10 weekly envelope, that pushes
   the held-out evaluation to ≈ $6–9 — leaving roughly nothing for
   re-runs or iteration.

2. **Marginal accuracy gain at small scale.** Jury voting tightens the
   judge's calibration *between* tasks, which matters most when a
   benchmark has 2,000+ tasks and any single judge's bias would push
   the leaderboard around. Our held-out is 8 (interim) → 48 (v0.1.0)
   tasks. At that scale, the inter-rater-agreement work documented in
   `inter_rater_agreement.md` (κ ≥ 0.80 on all four rubric dimensions
   after revision) is closer to load-bearing than a jury would be.

3. **Confounded with preference leakage.** Multiple judges from the same
   model family are not independent samples — they share base-model
   biases. To get the jury's nominal accuracy gain, we would need 3
   judges from 3 different families, which doubles routing complexity
   and creates an additional auditing surface for leakage.

## Operational consequence for our work

Single-judge evaluation, family-rotated. Inter-rater agreement is the
substitute for jury redundancy. We commit to revisiting this at v0.2 if
the held-out partition grows past ≈ 100 tasks; at that scale the trade-
off the paper recommends becomes attractive.
