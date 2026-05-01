# Methodology Rationale — Path B Selection

> Companion to [methodology.md](methodology.md). This document satisfies the
> Act III requirement: a one-page rationale that ties the chosen training
> path to a Tenacious-specific failure mode, cites at least three Week 10
> trace IDs, and cites at least two read papers with section references.
> Alternative paths are considered and dismissed.

## 1. The chosen path: B (preference-tuned judge / critic)

**One-line summary.** Train a small LoRA-adapted Qwen2.5-1.5B-Instruct judge
from `(chosen, rejected)` preference pairs and deploy it as a
rejection-sampling layer in front of the Week 10 generator.

**Why this and not Path A or Path C.** The Week 10 evidence does not show a
generator that *cannot* produce a good email. It shows a generator that
**cannot tell when its email is wrong** — an inconsistency failure, not a
generation-quality failure. The mismatch between Path A (treat the symptom
as a generation problem) and Path B (treat it as a recognition problem) is
load-bearing.

## 2. Week 10 trace evidence (≥ 3 trace IDs)

The three traces below all share the same shape: locally reasonable
next-token decisions that compound into a Tenacious-policy violation by the
end of the trajectory.

1. **`tr_dev_baseline_20260423_171204_task07_t2`** — `signal_overclaiming`.
   The drafter rendered a `LOW`-confidence `ai_maturity` score as an ASSERT
   ("you are clearly behind on AI maturity") in the email body. The brief
   showed `ai_maturity.confidence = LOW`; the policy required interrogative
   phrasing.  The generator produced grammatical, on-tone English at every
   step; the failure is that nothing in the trajectory recognised the
   confidence flag as load-bearing for the surface form. **Detected by
   probe P008 (LOW-conf funding → ASSERT, LLM 3/10).**

2. **`tr_dev_baseline_20260423_171204_task19_t1`** — `bench_overcommitment`.
   The drafter promised "12 senior Go engineers in two weeks" without
   inspecting `bench_summary.available_stacks` (Go = 4 senior). The bench
   check tool exists in the agent's tool repertoire; it was simply not
   called. A judge that fails the draft on bench-vs-brief mismatch would
   short-circuit the failure at zero training cost on the generator.
   **Detected by probe P012 (`_check_bench_match` invoked without
   `required_stacks`, orchestrator line 102).**

3. **`tr_dev_baseline_20260423_171204_task23_t4`** — `dual_control_handoff`.
   The agent called a destructive tool (`finalize_meeting_invite`) before
   the user's authentication step had completed. The tool call was
   syntactically valid; the trajectory state was not. **Detected by probe
   P023; ≈ 5/150 sims.** A trained judge that gates final-action emission
   on a `pre_action_safe_to_send` rubric would have caught this without
   any change to the generator.

Two additional traces extend the same pattern:
`tr_dev_baseline_20260423_171204_task41_t3` (gap-brief over-claiming, P032)
and `tr_dev_baseline_20260423_171204_task58_t1` (signal staleness, P031).
The full picture is six probes triggering on the same root cause across
five trace IDs — a recognition failure, not a generation failure.

## 3. Paper anchors (≥ 2, with section references)

1. **Gu et al. (2024–2025), *A Survey on LLM-as-a-Judge*** — §4.3 (compositional
   rubrics) and §6.2 (deployment as production gate). Documents the pattern
   of using a small judge to gate a larger generator and lists the failure
   modes a judge layer is good at suppressing — exactly the Tenacious
   inconsistency profile from §2 above. Our 4-component scorer
   (banned_phrases, grounding, tone, structural) is a direct application of
   the §4.3 compositional pattern.

2. **Meng, Xia & Chen (2024), *SimPO: Simple Preference Optimization with a
   Reference-Free Reward*** — §3 (algorithm) and Table 2 (5/6 benchmarks
   beat or matched DPO at lower cost). Picked over DPO for two reasons:
   reference-free (halves VRAM, fits a Qwen2.5-1.5B + LoRA on a free
   Colab T4) and demonstrated parity-or-better on the Meng et al.
   benchmark suite. ORPO (Hong, Lee & Thorne 2024) is the next-best
   alternative; we chose SimPO because the SimPO paper's recommended
   `learning_rate = 5e-6` and `beta = 2.0` are both stable on small
   preference sets, which matters at our 24-pair training scale.

3. **Li et al. (2025), *Preference Leakage*** — §2.2 (the leakage rule).
   Codifies the rule that the model that *generates* a chosen/rejected
   pair must not be the model that *judges* it. We enforce this at the
   family level: the rejected drafts come from the Week 10 agent
   (`anthropic` family); the chosen rewrites come from `deepseek`; the
   judge filter on each row is `qwen` or `deepseek` and is forbidden from
   matching the authoring family. The router enforces this in
   `generation_scripts/judge_filter.py:pick_judge` and the preference
   builder validates it in `training_data/build_preference_pairs.py:as_row`.

## 4. Alternatives considered and dismissed

### 4.1 Path A — SFT a generation component

A natural fit if the Week 10 generator produced *low-quality* emails. It
does not. Across the 150 dev-slice traces the agent produced grammatically
correct, on-tone English in every case — the failures are about which
*facts* it cited and *when* it should have asked instead of asserted. A
new generator trained on better drafts would still need to know when its
output is wrong, which is the recognition problem Path B targets.

The audit memo's `tone_marker_drift` axis (probes P015–P017) is the one
exception where Path A would be a credible alternative — the LLM-judge
scored generated drafts 1–3 / 5 on tone markers in 33 % of cases. We
dismissed Path A regardless because (a) the same data prep that builds
Path B preference pairs would also support Path A SFT, so the optionality
is preserved; and (b) Path B addresses *both* tone-marker drift and the
five other failure modes from one training run, not one.

### 4.2 Path C — Process reward model

A better fit for the τ²-Bench dual-control trajectory failures (probes
P023–P025) where the local-step correctness varies across a multi-step
trajectory. It would also be the strongest answer to the
`dual_control_handoff` axis specifically. We dismissed it for two
reasons:

1. **Per-step labelling cost.** The 1,622-line `trace_log.jsonl` has
   ≈ 8,000 individual decision steps after expansion. Per-step labelling
   at human throughput is ≈ 2 minutes / step → 260 hours, which exceeds
   the week's calendar budget and the $10 compute envelope (an LLM
   labeller at eval-tier rates would burn ≈ $30 alone, before any model
   training).
2. **Data-prep is the bottleneck per the brief.** The challenge document
   names data-prep as the highest-risk Day-4 step for Path C; the
   trade-off is unfavourable for a one-week deliverable.

A judge layer (Path B) catches the same dual-control failure pattern on
the *final* tool call rather than at every step. We sacrifice some
trajectory-aware sensitivity for a 30× cheaper data-prep budget.

## 5. Failure-mode-to-path mapping (the bottom line)

| Failure family | Week 10 evidence | Best path | Picked path | Why same? |
|---|---|---|---|---|
| Signal over-claiming (P007–P011) | LOW-conf rendered as ASSERT in 3 / 5 traces | **B** (recognition) | B | match |
| Bench over-commitment (P012–P014) | bench-check skipped on 3 / 3 traces | **B** (recognition) | B | match |
| Tone-marker drift (P015–P017) | 1-3/5 marker scores on 33 % of drafts | A *or* B | B | one training run covers both |
| Dual-control handoff (P023–P025) | tool fired before auth on 5 / 150 sims | **C** (trajectory) | B | data-prep cost; B catches at final step |
| Gap-brief over-claiming (P032–P034) | LOW-conf gap led emails on 4 / 12 cases | **B** (recognition) | B | match |
| Signal staleness (P029–P031) | scraper false-negative + stale window | **B** (recognition) | B | match |

Five of the six failure families are best-served by Path B directly. The
sixth (dual-control) is best-served by Path C in principle but is
addressable by Path B's final-step judge under the week's cost envelope.
This is the one place the analysis is honest about a slight loss of
sensitivity for a budget gain — and is the basis for the v0.2 coverage
gap entry on dual-control / trajectory-aware sub-task in
[FINAL_REPORT.md](FINAL_REPORT.md).
