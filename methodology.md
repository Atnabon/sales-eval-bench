# Methodology — Tenacious-Bench v0.1

## 1. Path declaration

**Path B — preference-tuned judge / critic.** Trained component is a small
classifier / preference scorer that grades agent outputs on Tenacious
dimensions and is deployed as a rejection-sampling layer in front of the
Week 10 generator.

### Justification (Week 10 evidence + paper anchors)

The Week 10 evidence does not point to a generator that *cannot* produce a
good email — it points to a generator that **cannot tell when its email is
wrong**. Across 150 dev-slice simulations the agent passed `pass@1 = 0.7267`
(`baseline.md`); the failures are *inconsistency* failures, not capability
failures. Three Week 10 traces make this concrete:

- `tr_dev_baseline_20260423_171204_task07_t2` — drafter renders a
  `LOW`-confidence `ai_maturity` score as an ASSERT in the email body.
- `tr_dev_baseline_20260423_171204_task19_t1` — drafter promises bench
  staffing without checking `bench_summary.available_stacks`.
- `tr_dev_baseline_20260423_171204_task23_t4` — agent calls a destructive
  tool before user authentication completes.

All three have the same shape: the locally-reasonable next token is correct
~70% of the time and brand-damaging the other 30%. Path A (SFT) treats this
as a generation-quality problem and adjusts the generator's distribution.
Path B keeps the existing distribution and adds an external checker —
exactly the SCAP rejection-sampling pattern we documented in
[`../conversion-engine/eval/probes/target_failure_mode.md`](../conversion-engine/eval/probes/target_failure_mode.md).

Paper anchors that reinforce the choice:

- **Gu et al. (2024–2025), *A Survey on LLM-as-a-Judge*** — the
  evidence base for using a small judge as a production gate. Section 4.3
  (compositional rubrics) maps directly onto our 4-component scorer.
- **Meng, Xia & Chen (2024), *SimPO*** — reference-free preference
  optimization. We pick SimPO over DPO because we can run it on Colab T4
  without a frozen reference model and because SimPO matched or beat DPO
  on 5 of 6 published benchmarks at lower cost.
- **Li et al. (2025), *Preference Leakage*** — codifies the rule that
  the model that *generates* a chosen/rejected pair cannot be the model
  that *judges* it. Our router (`generation_scripts/model_routes.yaml`)
  enforces this at the family level.

We considered **Path C (PRM)**. It is a better fit for the τ²-Bench
trajectory failures (P023–P025) but the per-step labelling cost on 1,622
trace lines exceeds our $10 budget for the week, and the data-prep is the
bottleneck per the brief. Path B addresses both Tenacious over-claiming
*and* the trajectory analog through the same SCAP rejection layer at much
lower data-prep cost.

## 2. Dimensions and source modes

### 2.1 Eleven dimensions

Mapped one-to-one onto the eleven probe categories from the Week 10 failure
taxonomy (`../conversion-engine/eval/probes/failure_taxonomy.md`). See
`tenacious_bench_v0.1/manifest.json` for counts per partition.

### 2.2 Four authoring modes (target shares)

| Mode | Target share | Cost driver | Anchor |
|---|---|---|---|
| trace_derived | ~30% | free; redaction + restructure | Week 10 `trace_log.jsonl` |
| programmatic_sweep | ~30% | dev-tier surface variation | Probe templates |
| multi_llm_synthesis | ~25% | frontier seed + dev-tier variant | Magpie (Xu et al., 2024) |
| hand_authored_adversarial | ~15% | human time only | Week 10 SCAP target |

The interim sample (44 tasks) currently shows **trace 27% / prog 30% /
synth 25% / hand 18%** — within ±3pp of the targets. Final v0.1.0 (240
tasks) will hit the targets exactly via the partition script.

## 3. Partitioning protocol

Stratified 50 / 30 / 20 across both dimension and source_mode. Stratification
guarantees each partition reflects the full failure surface — no partition
is allowed to be missing an entire dimension.

Held-out is sealed (see `tenacious_bench_v0.1/held_out/SEALED.md`). The
unsealed JSONL is gitignored. Sealing is performed by
`generation_scripts/seal_held_out.py` (Day 7 deliverable).

## 4. Contamination prevention

Three checks before the held-out is sealed. Run via
`generation_scripts/contamination_check.py`. Output: `contamination_check.json`.

| Check | Threshold | Status |
|---|---|---|
| 8-gram Jaccard between held_out and train | < 0.20 | PASS (max 0.142) |
| Cosine on `all-MiniLM-L6-v2` | < 0.85 | PASS (max 0.812) |
| Time-shift (every signal ref carries `signal_window_end`) | window ends ≥ 2025-08-01 | PASS (24/24) |

We deliberately use **MiniLM-L6** (not a frontier embedding) per the
challenge brief — the cost-discipline observable rewards using cheap models
for high-volume work and reserving eval-tier compute for sealed scoring.

## 5. Inter-rater agreement

Hand-labelled 30 dev tasks, then re-labelled them 24 hours later without
looking at the first labels. Agreement matrix in
[inter_rater_agreement.md](inter_rater_agreement.md). Aggregate Cohen's κ:

| Rubric dimension | κ |
|---|---|
| banned_phrases | 0.91 |
| grounding | 0.83 |
| tone | 0.79 |
| structural | 0.95 |

Tone scored under the 80% threshold on first pass. We revised the rubric
(added a worked-example block to each `tone_markers` entry) and relabelled
— second-pass κ for tone climbed to 0.86.

## 6. License

`tenacious_bench_v0.1/` released under **CC-BY-4.0**. Rationale:

- The dataset is built from public Crunchbase ODM + layoffs.fyi snapshots
  and a synthetic Tenacious style guide. None of the inputs carry
  inheritable share-alike obligations.
- The intended audience (the open evaluation community, especially
  agent-reliability researchers) is best served by permissive reuse.
- Attribution is required and is documented in `datasheet.md`.

Code under MIT. Adapter (Path B output) under CC-BY-4.0 with model card
limitations.

## 7. Reproducibility

```bash
SEED=20260422
python generation_scripts/contamination_check.py \
    --train tenacious_bench_v0.1/train/tasks.jsonl \
    --dev   tenacious_bench_v0.1/dev/tasks.jsonl \
    --held_out tenacious_bench_v0.1/held_out/tasks.jsonl \
    --out tenacious_bench_v0.1/contamination_check.json
```

A stranger should be able to clone, install, and reproduce the headline
contamination report and the four committed example evaluations in under
one hour. Verified on a clean macOS 14 / Python 3.11 environment on
2026-04-22 13:45 UTC.
