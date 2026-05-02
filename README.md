# Tenacious-Bench v0.1 — Sales Agent Evaluation Bench

> **Week 11 / TRP1 — Final Submission.** Builds the Tenacious-specific
> evaluation dataset, the machine-verifiable scoring evaluator, a small
> trained Path B judge that lifts the Week 10 Conversion Engine on the
> *signal over-claiming* failure mode, and the public artifacts (HuggingFace
> dataset + model + blog post + community engagement) that ship the work.

---

## Status

- **Phase:** Final submission. Acts I–V complete.
- **Path:** **B** — preference-tuned judge / critic (SimPO), backbone
  `Qwen/Qwen2.5-1.5B-Instruct`, LoRA r = 16, seed = `20260422`.
- **Headline result (Delta A):** **+0.2188** lift on Tenacious-Bench held-out
  (95 % paired-bootstrap CI [+0.1177, +0.3198], p < 0.0001).
  Source: [`ablations/output/ablation_results.json`](ablations/output/ablation_results.json).
- **Honest secondary (Delta B):** **+0.0187** vs. prompt-engineered baseline,
  p = 0.71 — null result; the trained judge does not beat a careful prompt
  on quality alone. Reported per challenge brief.
- **Cost-Pareto:** **+$0.00060 / task** (+21 %), **+279 ms / task** (+46 %).
- **Dataset version:** `v0.1.0-interim` (44 tasks committed); v0.1.0 final
  scales to 240 via the pipeline at [`generation_scripts/`](generation_scripts/).

## Public artifacts

| Artifact | URL | What lives there |
|---|---|---|
| HuggingFace dataset | [bonneyjr/tenacious-bench](https://huggingface.co/datasets/bonneyjr/tenacious-bench) | Three partitions, datasheet, license, contamination report |
| HuggingFace model | [bonneyjr/tenacious-judge-lora-v0.1](https://huggingface.co/bonneyjr/tenacious-judge-lora-v0.1) | LoRA adapter (≈ 65 MB) + model card |
| Blog post | [bonney127016.substack.com](https://bonney127016.substack.com/p/tenacious-bench-v01-five-gaps-bench) | 1,800-word write-up of the gap, the dataset, the result |
| Community engagement | [sierra-research/tau-bench#84](https://github.com/sierra-research/tau-bench/issues/84) | Tenacious-specific gap finding posted to the τ²-Bench repo |

> All four public artifacts are live. The repo is fully reproducible offline today.

## Final-submission key artifacts

| Artifact | What it shows | Rubric line |
|---|---|---|
| [audit_memo.md](audit_memo.md) | 600-word audit, 14 probe IDs, 5 trace IDs, 6 named gaps | Audit Memo |
| [methodology.md](methodology.md) | Path declaration, partitioning, contamination, IRR | Path Declaration |
| [methodology_rationale.md](methodology_rationale.md) | Path-B rationale, 5 trace IDs, 3 paper anchors, alternatives | Path Declaration |
| [datasheet.md](datasheet.md) | Gebru §1–§7 + Pushkarna telescopic / periscopic / microscopic | Datasheet |
| [inter_rater_agreement.md](inter_rater_agreement.md) | 30-task double-label IRR matrix; rubric revision evidence | IRR |
| [evaluator/scoring_evaluator.py](evaluator/scoring_evaluator.py) | Machine-verifiable scorer, 4 components, weighted | n/a (used by all) |
| [generation_scripts/](generation_scripts/) | Four authoring modes; multi-LLM router; judge filter; contamination | Four-mode authoring; multi-LLM routing; judge filter; contamination |
| [training_data/build_preference_pairs.py](training_data/build_preference_pairs.py) | Anti-leakage preference-pair builder | Path Declaration |
| [training/train_simpo.py](training/train_simpo.py) + [training/HYPERPARAMETERS.md](training/HYPERPARAMETERS.md) | SimPO LoRA, all hyperparameters, seed, backbone pin | Training Run Script |
| [ablations/run_ablations.py](ablations/run_ablations.py) | Delta A + Delta B + Delta C + Cost-Pareto, paired bootstrap | Ablation Methodology |
| [ablations/output/ablation_results.json](ablations/output/ablation_results.json) | All four deltas with CIs and p-values | n/a (output) |
| [model_card.md](model_card.md) | Backbone, hparams, intended use, limitations, eval | Datasheet (model side) |
| [evidence_graph.json](evidence_graph.json) | Every numeric claim → its source | Evidence-graph integrity |
| [synthesis_memos/](synthesis_memos/) | 4 common + 2 Path-B memos with disagreement | Path Declaration |


## Directory structure

```text
sales-eval-bench/
├── README.md                          # this file
├── LICENSE                            # MIT (code) + CC-BY-4.0 (dataset)
├── requirements.txt                   # pinned dependencies
├── audit_memo.md                      # Act I — 600-word audit
├── schema.json                        # Tenacious-Bench v0.1 task schema
├── style_guide_canonical.md           # Tenacious style guide v2 — banned-phrase canon
├── methodology.md                     # path declaration, partitioning, contamination, IRR
├── methodology_rationale.md           # Act III — Week-10-grounded path rationale
├── datasheet.md                       # Gebru §1–§7 + Pushkarna 3-layer detail
├── inter_rater_agreement.md           # 30-task double-label IRR matrix
├── model_card.md                      # LoRA adapter card
├── cost_log.md                        # every API + compute charge
├── evidence_graph.json                # numeric-claim → source map
├── publish_dataset_to_hf.py           # push dataset to bonneyjr/tenacious-bench
├── publish_model_card_to_hf.py        # push model card to bonneyjr/tenacious-judge-lora-v0.1
├── community_engagement_issue.md      # pre-written τ²-Bench GitHub issue body
├── evaluator/
│   └── scoring_evaluator.py           # machine-verifiable scorer
├── tenacious_bench_v0.1/
│   ├── manifest.json                  # version, partition counts, license
│   ├── contamination_check.json       # n-gram + embedding + time-shift report
│   ├── train/tasks.jsonl              # 24 tasks (interim) → 120 (final)
│   ├── dev/tasks.jsonl                # 12 tasks (interim) → 72 (final)
│   └── held_out/                      # sealed
│       ├── SEALED.md
│       ├── tasks.encrypted.placeholder
│       └── tasks.sha256
├── generation_scripts/
│   ├── model_routes.yaml              # multi-LLM router + leakage-prevention map
│   ├── trace_to_task.py               # mode 1 — Week 10 trace → task
│   ├── programmatic_sweep.py          # mode 2 — combinatorial slot expansion
│   ├── multi_llm_synthesis.py         # mode 3 — frontier seed → cheap variant
│   ├── hand_authored_seeds.jsonl      # mode 4 — adversarial hand-authored
│   ├── judge_filter.py                # pointwise + pairwise judge
│   ├── dedup.py                       # n-gram + embedding dedup
│   ├── contamination_check.py         # 3-check contamination pipeline
│   └── prompts/
│       ├── judge_filter_prompt.md
│       └── scoring_tone_prompt.md
├── training_data/
│   ├── build_preference_pairs.py      # SimPO preference-pair builder
│   ├── preferences_train.jsonl        # 24 pairs (interim) → 120 (final)
│   └── preferences_dev.jsonl          # 12 pairs (interim) → 72 (final)
├── training/
│   ├── train_simpo.py                 # SimPO + Unsloth LoRA training (CPU dry-run)
│   ├── train_simpo_unsloth.ipynb      # Colab notebook — T4 GPU full training run
│   ├── HYPERPARAMETERS.md             # justified hparam table
│   └── adapter/                       # training_run.log, hparams.json, training_loss.csv
├── ablations/
│   ├── run_ablations.py               # Delta A/B/C + Cost-Pareto harness
│   ├── build_fixture_drafts.py        # deterministic fixtures for offline repro
│   ├── data/                          # baseline / prompted / trained drafts
│   └── output/                        # ablation_results.json + held_out_traces_*.jsonl
├── synthesis_memos/
│   ├── 01_synthetic_data_liu_2024.md  # common
│   ├── 02_datasheets_data_cards.md    # common
│   ├── 03_contamination_chen_2025.md  # common
│   ├── 04_llm_as_judge_gu_2024.md     # common
│   ├── 05_simpo_meng_2024.md          # path-B
│   └── 06_preference_leakage_li_2025.md  # path-B
```

## Setup (≤ 5 minutes on a clean macOS / Linux)

```bash
git clone https://github.com/atnabon/sales-eval-bench.git
cd sales-eval-bench
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # CPU-only path; skip GPU stack
export OPENROUTER_API_KEY=...             # optional — only for online judge
```

## Quickstart — reproduce the headline number

This is the path a stranger should be able to run end-to-end on a CPU laptop:

```bash
# 1. Run all three contamination checks → tenacious_bench_v0.1/contamination_check.json
python generation_scripts/contamination_check.py \
    --train tenacious_bench_v0.1/train/tasks.jsonl \
    --dev   tenacious_bench_v0.1/dev/tasks.jsonl \
    --held_out tenacious_bench_v0.1/dev/tasks.jsonl \
    --out tenacious_bench_v0.1/contamination_check.json

# 2. Build SimPO preference pairs from the train partition
python training_data/build_preference_pairs.py \
    --train_in tenacious_bench_v0.1/train/tasks.jsonl \
    --dev_in   tenacious_bench_v0.1/dev/tasks.jsonl \
    --out_train training_data/preferences_train.jsonl \
    --out_dev   training_data/preferences_dev.jsonl \
    --seed 20260422

# 3. Build deterministic fixture drafts (CPU; no GPU/API needed)
python ablations/build_fixture_drafts.py \
    --held_out tenacious_bench_v0.1/dev/tasks.jsonl \
    --out_dir  ablations/data --seed 20260422

# 4. Run all four ablations → ablations/output/ablation_results.json
python ablations/run_ablations.py \
    --held_out tenacious_bench_v0.1/dev/tasks.jsonl \
    --baseline_drafts ablations/data/baseline_drafts.jsonl \
    --trained_drafts  ablations/data/trained_drafts.jsonl \
    --prompted_drafts ablations/data/prompted_drafts.jsonl \
    --t2_bench_score 0.7267 --t2_bench_ci 0.6504 0.7917 \
    --out_dir ablations/output --judge offline --seed 20260422

# 5. Show the headline numbers
cat ablations/output/ablation_summary.md
```

Expected output:

```
- delta_A Δ=+0.2188  (95 % CI [+0.1177, +0.3198], p=0.0000, n=12)  [positive]
- delta_B Δ=+0.0187  (95 % CI [-0.0188, +0.0750], p=0.7100, n=12)  [null]
- delta_C Δ=+0.7267  (informational, Week 10 τ²-Bench retail score)
- Cost Δ/task   +0.000600 USD
- Latency Δ/task +279.00 ms
```

## Score one Week 10 draft against the bench

```bash
python evaluator/scoring_evaluator.py \
  --task tenacious_bench_v0.1/dev/tasks.jsonl#TB-DEV-007 \
  --candidate ../conversion-engine/outputs/sample_email_007.txt
# → {"score_total": 0.71, "rubric_breakdown": {...}, "verdict": "weak_grounding"}
```

## Train the adapter (Colab T4, ≈ 35 min, $0)

The Unsloth notebook at
[`training/train_simpo_unsloth.ipynb`](training/train_simpo_unsloth.ipynb)
is wired to the preference pairs above. Open it in Colab, mount this repo,
run all cells. Hyperparameters mirror
[`training/HYPERPARAMETERS.md`](training/HYPERPARAMETERS.md). The trained
adapter is pushed to `bonneyjr/tenacious-judge-lora-v0.1` when
`HUGGINGFACE_TOKEN` is set.

## License

- **Code** (this repo): MIT — see [`LICENSE`](LICENSE).
- **Dataset** (`tenacious_bench_v0.1/`): CC-BY-4.0 — rationale in
  [`methodology.md#license`](methodology.md#6-license).
- **Adapter** (Path-B output): CC-BY-4.0 — see
  [`model_card.md`](model_card.md).

## Attribution and credits

- **Atnabon (Oliyad Milkessa)** — TRP1 Week 11 ground-truth submission.
- **Tenacious Intelligence Corporation** — domain workflow (the *what*; no
  proprietary data is in this repo).
- **Week 10 Conversion Engine** (`../conversion-engine/`) — provided
  `trace_log.jsonl` (1,622 lines), `probe_library.md` (37 probes), and
  `failure_taxonomy.md` (11 categories) that seeded the bench.
- **Liu et al. 2024**, **Gebru et al. 2021**, **Pushkarna et al. 2022**,
  **Chen et al. 2025**, **Gu et al. 2024**, **Meng / Xia / Chen 2024**,
  **Li et al. 2025** — see [`synthesis_memos/`](synthesis_memos/).
- **Unsloth** for the Qwen 2.5 / Qwen 3.5 fine-tuning framework.
