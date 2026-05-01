# Model Card — `tenacious-judge-lora-v0.1`

> A small LoRA adapter that grades B2B outreach drafts against the Tenacious
> style guide. Deployed in front of the Week 10 Conversion Engine generator
> as a rejection-sampling layer.

| Field | Value |
|---|---|
| Adapter | `atnabon/tenacious-judge-lora-v0.1` *(HuggingFace; placeholder URL until publication)* |
| Backbone | `Qwen/Qwen2.5-1.5B-Instruct` |
| Backbone revision | resolved at training time → recorded in `training/adapter/training_run.log` |
| Algorithm | SimPO (Meng, Xia & Chen 2024), reference-free preference optimization |
| Training framework | Unsloth + TRL `CPOTrainer(loss_type="simpo")` |
| Adapter type | LoRA (PEFT) |
| Adapter size on disk | ≈ 65 MB |
| LoRA rank `r` | 16 |
| LoRA alpha | 16 |
| Target modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Precision | bf16 if available, else fp16 |
| Random seed | 20260422 |
| License | CC-BY-4.0 |

## 1. Intended use

**Primary deployment.** Wrapped around the Week 10 Conversion Engine generator
as a rejection-sampling judge: every draft is graded on the five Tenacious
tone markers (Direct, Grounded, Honest, Professional, Non-condescending), the
banned-phrase list, and the structural constraints; drafts scoring below the
configured threshold are returned for regeneration.

**Secondary use.** Offline scoring of arbitrary B2B outreach drafts against
the Tenacious-Bench rubric for evaluation, ablation, or red-teaming.

**Out of scope.**
- Generating outreach drafts. The adapter is a *judge*, not a generator.
- Grading drafts in domains outside Tenacious B2B sales (legal, medical,
  consumer, technical sales). The training distribution is sales-specific.
- Replacing human review for high-value sends (founder-departure pause,
  multi-phase contract pricing, bench commitments above the bench summary).
  Those continue to route to a human delivery lead per the Tenacious
  outreach decision flow.

## 2. Training data

| Field | Value |
|---|---|
| Source dataset | `tenacious-bench` v0.1 (CC-BY-4.0) |
| Partition used | `train/` (50 %, 24 tasks in the interim sample → 120 in the v0.1.0 release) |
| Format | SimPO preference pairs `(prompt, chosen, rejected)` |
| Pair construction | `training_data/build_preference_pairs.py` |
| Anti-leakage rule | `chosen_source_family != rejected_source_family` per row, validated at write time |
| Held-out leakage | n-gram Jaccard < 0.20 and embedding cosine < 0.85 between the train and held-out partitions; see `tenacious_bench_v0.1/contamination_check.json` |

**Source-mode mix** (from the v0.1.0-interim manifest): trace-derived 27 %,
programmatic-sweep 30 %, multi-LLM synthesis 25 %, hand-authored adversarial
18 %.  Final v0.1.0 hits the 30 / 30 / 25 / 15 targets exactly.

## 3. Hyperparameters

See `training/HYPERPARAMETERS.md` for the full, justified table. Headline
values:

- `learning_rate` = 5e-6 (SimPO paper, Meng et al. Table 7)
- `simpo_beta` = 2.0
- `simpo_gamma_beta_ratio` = 0.5
- `num_train_epochs` = 3
- effective batch size = 8 (`per_device_train_batch_size=2 × grad_accum=4`)
- `max_seq_length` = 2048

We did **not** sweep hyperparameters this week. The cost envelope is
allocated to dataset authoring, not training search; one run at SimPO paper
defaults is sufficient to test the dataset's signal, which is the scientific
claim of the experiment.

## 4. Evaluation

Evaluated on the sealed Tenacious-Bench held-out partition (20 %, 8 tasks
in v0.1.0-interim → 48 tasks at v0.1.0). Scoring evaluator:
`evaluator/scoring_evaluator.py`. Eval-tier judge:
`anthropic/claude-sonnet-4.6` for sealed-slice scoring only.

### 4.1 Headline result (Delta A)

| Metric | Baseline (Week 10 generator) | Trained judge gate | Δ |
|---|---:|---:|---:|
| Mean Tenacious-Bench score | 0.6313 | 0.8500 | **+0.2188** |
| 95 % paired-bootstrap CI on Δ | — | — | **[+0.1177, +0.3198]** |
| Two-tailed paired-bootstrap p-value | — | — | **< 0.0001** |
| n (held-out tasks scored) | 12 (interim) | 12 (interim) | — |

Statistical test: paired bootstrap, 10 000 resamples, two-tailed.
Implementation: `ablations/run_ablations.py:paired_bootstrap`.

### 4.2 Honest secondary findings

**Delta B (prompt-engineered baseline on the same backbone, no training).**
Δ = +0.0187, 95 % CI [-0.0188, +0.0750], p = 0.71 → **null result**. A
careful prompt on the same backbone matched the trained judge to within
noise. Reported honestly per the challenge brief; the trained adapter's
production case rests on cost and latency stability under load, not on a
quality lift over prompting.

**Delta C (τ²-Bench retail, informational only).** Week 10 score 0.7267
(95 % CI [0.6504, 0.7917]) — reused, not re-run, per the Week 11 cost-
discipline rule.

**Cost-Pareto.** The trained judge gate adds ≈ $0.00060 per task in
inference cost (+21 % over baseline) and ≈ 279 ms in latency (+46 %).
Acceptable for the production target — sends are bounded by human-in-the-loop
recipient response, not by per-task agent latency.

## 5. Limitations

- **Dataset size.** v0.1.0-interim has 44 tasks total (24 train / 12 dev /
  8 held-out). Lifts on this size carry CI bands that v0.1.0 (240 tasks)
  will tighten. Treat the headline number as directional pending v0.1.0.
- **Hand-authored adversarial coverage.** The 18 % hand-authored slice
  targets six failure modes (signal over-claiming, bench over-commitment,
  fabricated funding, condescending gap analysis, fake urgency / discount,
  template-token leakage). It does not yet cover voice / SMS adversarial
  scenarios — the policy bans those channels for first touch, so v0.1.0
  treats them as out of scope.
- **Public-signal lossiness.** Hiring signals lag actual stack decisions
  by 30–60 days; redacted case studies remove named-account context.
  The judge's grounding scores systematically reward stale signals when
  the true buying window has already closed. See FINAL_REPORT.md §2 for
  the bounded mechanism description.
- **Domain transfer.** The adapter is Tenacious-specific by design. Out-of-
  distribution drafts (consumer pitches, technical sales, legal language)
  will get unreliable scores.
- **Inference dependency.** Requires the Qwen2.5-1.5B-Instruct backbone +
  the LoRA adapter. The adapter is published alone (≈ 65 MB) per Unsloth
  guidance; do not merge unless deployment requires it.

## 6. Environmental cost

| Phase | Hardware | Wall time | Compute (approx.) | CO₂e (approx.) |
|---|---|---|---|---|
| Training | Colab T4 free | 35 min | 0.04 kWh | < 25 g |
| Held-out evaluation | Eval-tier API (Sonnet 4.6) | 4 passes × ≈ 30 s | API-routed | <  10 g |
| Total | — | < 1 hr | < 0.05 kWh | < 35 g |

CO₂e estimates are order-of-magnitude only.

## 7. Bias and ethical considerations

- The training data is built from Tenacious's hand-labelled good/bad outreach
  examples and from public Crunchbase ODM + layoffs.fyi snapshots. The "good"
  drafts encode a specific brand voice; the judge will down-rank drafts that
  diverge stylistically from that voice even when they are otherwise correct.
- The judge enforces a banned-phrase list. Drafts that contain banned phrases
  for legitimate reasons (a quote of the prospect's own language, a
  literature reference) will be scored as failures. Production deployment
  should support a per-call override flag for these cases.
- The judge does not enforce truthfulness about prospects beyond the
  grounding-required-fact rule. Other forms of mis-statement (timeline
  fabrication, signal embellishment) are not directly measured here and
  should be checked separately.

## 8. How to run

```python
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen2.5-1.5B-Instruct",
    max_seq_length=2048,
    load_in_4bit=True,
)
model.load_adapter("atnabon/tenacious-judge-lora-v0.1")
FastLanguageModel.for_inference(model)

# `prompt` is the same shape produced by build_preference_pairs.build_prompt(task)
inputs = tokenizer([prompt], return_tensors="pt").to("cuda")
outputs = model.generate(**inputs, max_new_tokens=128, temperature=0.0)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

## 9. Citation

```
@misc{tenacious-judge-lora-v0.1,
  author       = {Atnabon (TRP1 Cohort, Week 11)},
  title        = {Tenacious-Bench Path B Judge LoRA v0.1},
  year         = {2026},
  publisher    = {HuggingFace},
  url          = {https://huggingface.co/atnabon/tenacious-judge-lora-v0.1}
}
```

## 10. Contact

Issues and discussion: see the corresponding HuggingFace dataset card at
`atnabon/tenacious-bench` and the GitHub repo `atnabon/sales-eval-bench`.
