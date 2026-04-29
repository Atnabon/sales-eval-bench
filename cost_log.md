# Cost Log — Week 11 Tenacious-Bench

Every API call and every compute charge is logged here with timestamp,
bucket, purpose, and amount. Per the challenge brief: the cost log is
itself a graded artifact, and the cost discipline of the week is a
Pareto observable.

**Budget envelope:** $10 total. Buckets: dataset authoring $3-5, training
$0-5, held-out evaluation $2-3, reserve $1-2.

**Two non-negotiable rules:**
- No τ²-Bench retail validation runs.
- No eval-tier model on Days 2–3.

## Day 0 — 2026-04-20

| Time (UTC) | Bucket | Purpose | Model / Compute | Amount |
|---|---|---|---|---|
| 09:14 | reserve | OpenRouter account warmup test | qwen3-next-80b-a3b | $0.002 |
| 09:21 | reserve | HuggingFace token validation | n/a | $0.000 |
| 11:48 | reserve | Unsloth Qwen 3.5 0.8B starter notebook (5-task dummy LoRA, T4) | Colab T4 free | $0.000 |
| **Total** | | | | **$0.002** |

## Day 1 — 2026-04-21

| Time (UTC) | Bucket | Purpose | Model / Compute | Amount |
|---|---|---|---|---|
| 14:02 | dataset_authoring | Audit memo dry-run (drafter sanity test, 10 sample emails) | qwen3-next-80b-a3b | $0.038 |
| 16:11 | dataset_authoring | Frontier-seed adversarial test (10 emails on `LOW`-confidence brief) | claude-sonnet-4.6 | $0.412 |
| 16:47 | dataset_authoring | Frontier-seed comparison (10 emails, same brief) | gpt-5 | $0.385 |
| **Total** | | | | **$0.835** |

## Day 2 — 2026-04-22 (interim work)

| Time (UTC) | Bucket | Purpose | Model / Compute | Amount |
|---|---|---|---|---|
| 11:14 | dataset_authoring | Programmatic-sweep batch P012 (20 variants, judge-filtered) | qwen3-next-80b-a3b | $0.092 |
| 11:18 | dataset_authoring | Programmatic-sweep batch P007 (20 variants, judge-filtered) | qwen3-next-80b-a3b | $0.087 |
| 11:34 | dataset_authoring | Programmatic-sweep batch P027 (12 variants) | deepseek-v3.2 | $0.061 |
| 11:46 | dataset_authoring | Programmatic-sweep batch P031 (10 variants) | deepseek-v3.2 | $0.052 |
| 11:55 | dataset_authoring | Multi-LLM synthesis seeds (8 hardest, frontier) | claude-sonnet-4.6 | $0.331 |
| 12:02 | dataset_authoring | Multi-LLM synthesis seeds (4 hardest, alternate) | gpt-5 | $0.158 |
| 12:08 | dataset_authoring | Variant expansion (8 seeds × 5 variants) | qwen3-next-80b-a3b | $0.171 |
| 12:11 | dataset_authoring | Variant expansion (4 seeds × 5 variants) | deepseek-v3.2 | $0.094 |
| 12:38 | dataset_authoring | Judge filter pass — pointwise on 240 candidates | qwen3-next-80b-a3b | $0.288 |
| 12:51 | dataset_authoring | Judge filter pass — preference-leakage rotation (deepseek where qwen authored) | deepseek-v3.2 | $0.142 |
| 13:02 | dataset_authoring | Contamination-check embedding pass (local, MiniLM) | local CPU | $0.000 |
| 13:14 | dataset_authoring | IRR calibration spot-check (10 sampled tasks double-scored) | claude-sonnet-4.6 (held for Day 6) | $0.000 (deferred) |
| **Day 2 total** | | | | **$1.476** |

## Cumulative through interim submission

| Bucket | Spent | Envelope | Remaining |
|---|---|---|---|
| dataset_authoring | $2.311 | $5.000 | $2.689 |
| training | $0.000 | $5.000 | $5.000 |
| held-out evaluation | $0.000 | $3.000 | $3.000 |
| reserve | $0.002 | $2.000 | $1.998 |
| **Cumulative** | **$2.313** | **$10.000** | **$7.687** |

## Notes

- **No τ²-Bench retail re-runs.** The Week 10 score of `pass@1 = 0.7267
  (95% CI 0.6504-0.7917)` is reused as the informational reference per
  `../conversion-engine/baseline.md`.
- **No eval-tier model use during authoring.** Claude Sonnet 4.6 was used
  for *seed* authoring (frontier-tier role), not for *judging* during
  authoring iteration. The eval-tier judge runs only on the sealed
  held-out, planned for 2026-04-26 / Day 6.
- **Frontier vs eval-tier distinction:** the same model (Claude Sonnet 4.6)
  fills both the frontier-seed role (allowed Days 2–3) and the eval-tier
  judge role (allowed Day 6 only). The role is distinguished by the
  caller, not the model — see `generation_scripts/model_routes.yaml`.

## Plan for Days 4–7

| Day | Bucket | Estimated spend |
|---|---|---|
| Day 4 (data prep, preference pair generation) | dataset_authoring | $1.20 |
| Day 5 (training, Colab T4) | training | $0.00 |
| Day 5 (training, RunPod fallback if Colab caps hit) | training | up to $3.00 |
| Day 6 (held-out eval, eval-tier judge × 4 passes) | held-out evaluation | $2.40 |
| Day 7 (publish + community) | reserve | $0.20 |
| **Forecast remainder** | | **$3.80–$6.80** |
| **Forecast week total** | | **$6.11–$9.11 / $10.00 cap** |
