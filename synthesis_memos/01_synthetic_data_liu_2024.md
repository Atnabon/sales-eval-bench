# Synthesis Memo 01 — Best Practices and Lessons Learned on Synthetic Data for Language Models

> Liu et al., COLM 2024. Reading status: completed 2026-04-21 evening.
> Memo style: paragraph-form. The grading bar is whether I can disagree
> with the paper on a specific design choice and justify the disagreement
> against my own evidence — not whether I can summarize.

## What I take from the paper

Liu et al. give the operational reference for the dataset-authoring choices
in Acts I–II. The strongest claims I am acting on:

1. **Quality > quantity at small scale.** §3.2 documents that synthetic
   datasets at the 1k–3k scale outperform 10k–30k unfiltered datasets when
   the small set is judge-filtered with explicit rubric thresholds.
2. **Multi-source synthesis dominates single-model synthesis.** §4.1
   shows that mixing frontier-seeded and dev-tier-expanded data yields more
   robust downstream training than either alone.
3. **Rubric-driven filtering > heuristic filtering.** §5 — pointwise judge
   scores on coherence + verifiability + clarity beat generic perplexity
   filters for downstream task performance.
4. **Difficulty stratification matters.** §6.3 — at small scale, a
   uniform distribution over difficulty hurts; an oversample of "hard"
   wins.

My v0.1 schema mirrors all four: 4-mode authoring with 25–30% from
multi-LLM synthesis, three-pointwise-dim judge filter at threshold 4/5,
explicit `difficulty` enum with adversarial oversampling.

## Where I disagree

**Claim under disagreement (§4.1 Table 3):** the paper recommends a 50/50
split between frontier seed and dev-tier variant for "best results."

**My disagreement:** for **adversarial-edge data** anchored to specific
documented failure modes, 50/50 understates the value of frontier seeds.
The Week 10 evidence shows that the highest-cost failures (signal
over-claiming on `LOW`-confidence inputs) are subtle enough that dev-tier
models often *fail to author the failure pattern at all* — the
dev-tier-generated variants are too clean.

**The evidence:** I ran an unscored dry-run on 2026-04-22 morning. Asked
Qwen3-Next to write 10 outreach emails for a brief with `ai_maturity:{score:2,
confidence:LOW}`. Qwen produced 8/10 emails that *correctly* hedged the
maturity score. Asked Claude Sonnet 4.6 with the same input but with the
adversarial framing "draft an email that a Tenacious style reviewer would
reject for over-claiming." Claude produced 9/10 emails that genuinely
exhibited the failure mode — useful as `reference_rejected` in preference
pairs.

**My adjusted ratio:** for **rejected** examples (the failure-mode
demonstrations), 80/20 in favor of frontier. For **chosen** examples (the
fix), 30/70 in favor of dev-tier — the dev-tier model is actually better
at producing on-style boring-but-correct text. Recorded in
`generation_scripts/model_routes.yaml#rotation_policy`.

## Where the paper is right and I am following it exactly

§5.4 — the *order* of the filter matters. Dedup before judge filter wastes
judge calls; judge filter before dedup wastes dedup compute. We dedup
*after* judge filter, which is the paper's recommendation, because the
judge filter is more expensive per call than the dedup hash table.

§6.1 — log every authoring run with a fixed seed and the model route. We
do this in `generation_scripts/model_routes.yaml` and emit per-batch
provenance into every task's `metadata.authoring_model`.

## Where this changes Day 4 design

For the Path B preference data (Day 4), I will use:

- **Rejected** samples: 60% from observed Week 10 drafter outputs (free,
  highest fidelity), 40% from frontier-authored adversarial seeds (paid,
  ~$1.50 budget envelope).
- **Chosen** samples: 70% dev-tier (Qwen / DeepSeek) rewrites of the
  rejected samples, 30% hand-authored corrections from my Week 10
  hand-fixes.

Family-leakage rule from Li et al. (2025): chosen and rejected for the
same task must come from different families. The router enforces this
automatically.

## Word count

~520 words.
