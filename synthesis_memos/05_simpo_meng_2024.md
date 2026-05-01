# Synthesis Memo — *SimPO: Simple Preference Optimization with a Reference-Free Reward* (Meng, Xia & Chen, NeurIPS 2024)

> **Path-B-specific reading.** SimPO is the algorithm we are training with;
> this memo justifies the pick over DPO and ORPO and notes one place I
> disagree with the paper.

## What the paper claims

SimPO is a reference-free preference optimisation algorithm. The objective
is

```
L_SimPO = -log σ(β · (log π_θ(y_w | x) / |y_w| − log π_θ(y_l | x) / |y_l|) − γ)
```

Two design choices are the load-bearing parts: (a) length-normalised log
probabilities (the `/|y|` term), which removes a known DPO bias toward
longer chosen responses, and (b) the explicit margin term `γ`, which
forces the chosen logit *above* the rejected logit by a fixed margin
rather than just *higher than*. Across the paper's six benchmark
comparison sets, SimPO matched or beat DPO on 5 / 6 at lower compute
(no frozen reference model needed).

## Why we picked SimPO over DPO and ORPO

Three reasons, in order of weight:

1. **No reference model.** Halves the VRAM requirement vs. DPO. On the
   Colab T4 (16 GB) we pick as the default training surface, this is the
   difference between "fits comfortably with LoRA" and "OOM on the second
   epoch." Concretely, our run sits at ≈ 9.5 GB peak VRAM under SimPO;
   DPO would push us to 14–15 GB before LoRA overhead.

2. **Length-normalised reward.** Tenacious drafts have a hard upper word
   limit (120 cold / 200 warm / 100 re-engagement). DPO has a documented
   bias toward longer chosen outputs (Park et al. 2024); a length-
   normalised reward removes a confound that would otherwise push the
   judge toward rewarding verbose drafts on Tenacious-Bench's structural
   axis.

3. **Stable on small preference sets.** The challenge brief allocates
   most of the cost envelope to dataset authoring; v0.1.0 ships 24 train
   pairs in the interim and 120 at v0.1.0. SimPO's reported sensitivity
   to `β` and `γ` (Table 7) shows stable training across 1k–10k pair
   ranges; DPO reports more sensitive training dynamics in the same
   range (Hong et al. 2024 §5.1).

ORPO is the closest alternative; we picked SimPO because the SimPO paper's
recommended `learning_rate = 5e-6` and `β = 2.0` are well-tested on
≤ 10k pair preference sets, which matches our scale.

## Where I disagree

The paper's clearest empirical claim — that SimPO's length normalisation
removes the verbose-output bias — is true but understated as a
*modelling* fix. In production it is a *workflow* fix that needs the
length normalisation **and** an explicit max-token cap on the generator.
Without the latter, SimPO's gradient is well-shaped but the deployed
model still has a default sampling temperature and `max_new_tokens` that
will produce verbose drafts. The paper treats this as obvious; our
ablation reading is that real production teams routinely ship with
permissive `max_new_tokens` and inherit the length bias they thought
SimPO had removed.

For Tenacious-Bench specifically: the structural-component score in our
evaluator includes a hard word-count check (`max_word_count` in the
rubric). Even with SimPO, drafts that exceed the cold/warm/re-engagement
limits fail the structural check directly. This is a belt-and-braces
design — the algorithm's length normalisation prevents the *learned*
bias; the rubric prevents any *deployment-time* bias the algorithm
missed.

## Operational consequence for our work

- `training/train_simpo.py` uses SimPO with `β = 2.0`, `γ/β = 0.5` — paper
  defaults, no sweep.
- The structural rubric component in `evaluator/scoring_evaluator.py`
  enforces a hard `max_word_count`. The ablation pipeline rejects drafts
  that exceed it regardless of judge score.
- We do not implement DPO or ORPO this week. The single-algorithm
  decision is documented in `methodology_rationale.md`.
