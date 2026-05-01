# Training Hyperparameters — Tenacious-Bench Path B

> **Path:** B (preference-tuned judge / critic, SimPO).
> **Backbone:** `Qwen/Qwen2.5-1.5B-Instruct` (HF revision pinned at run time
> and recorded in `training_run.log`).
> **Adapter:** LoRA only (no full fine-tune; budget envelope $0).

## Pinned values

| Hyperparameter | Value | Source |
|---|---|---|
| Backbone | `Qwen/Qwen2.5-1.5B-Instruct` | Unsloth Qwen 2.5 starter |
| Backbone revision | resolved at runtime → logged | reproducibility |
| LoRA rank `r` | 16 | Unsloth recommended for sales tone |
| LoRA `alpha` | 16 | matches `r` for a 1.0 effective scale |
| LoRA `dropout` | 0.0 | Unsloth-optimized |
| LoRA `target_modules` | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj | Unsloth canonical 7 |
| LoRA `bias` | none | Unsloth-optimized |
| `max_seq_length` | 2048 | brief + style guide + draft fits in 1.6k tokens |
| `per_device_train_batch_size` | 2 | T4 16 GB VRAM ceiling |
| `gradient_accumulation_steps` | 4 | effective batch 8 |
| `num_train_epochs` | 3 | loss flattens by epoch 2 on the 24-pair set |
| `learning_rate` | 5e-6 | Meng et al. (SimPO) Table 7 |
| `warmup_steps` | 5 | small dataset |
| `lr_scheduler_type` | cosine | TRL default |
| `weight_decay` | 0.0 | preference-tuning convention |
| `simpo_beta` | 2.0 | SimPO paper default |
| `simpo_gamma_beta_ratio` | 0.5 | SimPO paper default |
| `seed` | 20260422 | repo-wide reproducibility seed |
| Precision | bf16 if available else fp16 | T4 supports fp16; L4/A40 supports bf16 |

## Anti-leakage invariant (training data)

For every training row, `chosen_source_family != rejected_source_family`.
Validated in `training_data/build_preference_pairs.py:as_row()` and
re-checked in `train_simpo.py` before the trainer is constructed.

## Wall-time expectations

| Hardware | Expected wall time | Compute cost | Notes |
|---|---|---|---|
| Colab T4 (free) | 30–45 min | $0 | default; first kernel compile ~6 min |
| Colab Pro L4 | 12–18 min | covered by Pro sub | bf16 |
| RunPod community 4090 | 8–12 min | ~$0.05 | budget alternative if Colab caps |

If loss has not dropped below 0.5 by step 30, kill and inspect the data —
do not throw more compute at it. (Common root causes: chosen/rejected
quality gap is too small; preference pairs are mode-imbalanced.)

## What the hyperparameters control

- **Beta (SimPO).** Higher beta → sharper preference margin → faster
  convergence but easier to overfit on a 24-pair training set. 2.0 is the
  paper default; we did not sweep.
- **Gamma/beta ratio (SimPO).** Margin term that pushes the chosen logit
  *above* the rejected logit by a fixed margin. 0.5 is the paper default.
- **LoRA r.** Rank of the low-rank adapter. 16 is the Unsloth default for
  sales-tone work and produces a 50–80 MB adapter that fits in budget.

## What we did NOT sweep (and why)

We deliberately did not sweep hyperparameters this week. The challenge
brief allocates the cost envelope to dataset authoring, not to training
search. A single run at the SimPO paper defaults is sufficient to test
whether the dataset is signal-bearing — which is the scientific claim of
Acts I–IV — and is what the ablation harness in `ablations/` evaluates.

## Cost discipline

Recorded in `cost_log.md`:

| Bucket | Allocated | Spent | Variance |
|---|---|---|---|
| Dataset authoring | $3–5 | TBD | TBD |
| Training | $0–5 | $0 (Colab free) | $0 saved |
| Held-out evaluation | $2–3 | TBD | TBD |
| Reserve | $1–2 | TBD | TBD |
| **Total envelope** | **$10** | **TBD** | **TBD** |
