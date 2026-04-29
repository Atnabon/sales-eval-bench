# Audit Memo — Why τ²-Bench Retail Cannot Grade the Tenacious Conversion Engine

**Author:** Atnabon. **Date:** 2026-04-22. **Word count:** 598.

## The question

τ²-Bench retail measures whether an agent can complete a constrained
customer-service trajectory under dual-control with a simulated user. Tenacious
sells a different product through a different motion: signal-grounded outbound
B2B outreach where the cost of one over-claim is a $66K expected-value contact
burned at the brand-trust level. Across 150 dev-slice simulations our Week 10
agent scored **pass@1 = 0.7267 (95% CI 0.6504–0.7917)**
([baseline.md](../conversion-engine/baseline.md)) — a respectable retail score
that says nothing about Tenacious-specific behavior.

## What τ²-Bench retail does not grade

1. **Per-signal confidence honesty.** τ²-Bench accepts an answer if the action
   completes; it never asks whether the answer's grounding language matches its
   evidence strength. Probe **P007** (weak hiring → "aggressive hiring", LLM
   1/10) and **P008** (LOW-confidence funding → ASSERT, LLM 3/10) both pass
   τ²-Bench by construction because retail tasks have no `ai_maturity`
   confidence axis.
2. **Bench over-commitment.** Probes **P012/P013/P014** all `DET:FAIL`
   (`_check_bench_match()` invoked without `required_stacks`,
   orchestrator line 102) and τ²-Bench has no analog tool for "promise N
   senior MLEs from a bench you do not have". Per-incident cost is $240K.
3. **Tone-marker drift on the Tenacious style guide.** P015 ("bench" echo,
   LLM 3/10), P016 (hype vocabulary, LLM 0/20), and P017 (regen-still-low,
   LLM 1/5) are graded against the 12 hand-labeled "good" / 12 "bad" drafts in
   the v2 style guide — material τ²-Bench has never seen.
4. **Gap-brief over-claiming.** P032 (LOW-conf gap leads email, LLM 4/5) and
   P034 (`prospect_has_it=False` against confidence-less data, DET:FAIL) live
   on a `competitor_gap_brief` data shape τ²-Bench does not model.
5. **Time-shifted signal reliability.** Layoffs.fyi and Crunchbase ODM rows
   carry a `discovered_at` window. Probe **P031** (scraper false-negative)
   asks the agent to abstain when signal staleness exceeds 90 days — τ²-Bench
   has no temporal axis at all.
6. **Dual-control parallel.** P023 (destructive without confirm, ~5/150 sims),
   P024 (skip auth, ~2/150), and P025 (fabricated `order_id`, ~1/150) are the
   one place τ²-Bench *does* grade us — but it grades them as binary task
   failures, not as instances of a single ASSERT-when-ASK-was-required class
   that, on the Tenacious side, also drives signal over-claiming.

## What our Week 10 evidence proves

Across the 150-sim dev run, **trace IDs `tr_dev_baseline_20260423_…task07_t2`,
`…task19_t1`, `…task23_t4`, `…task41_t3`, and `…task58_t1`** all show the same
signature: the agent reached a state where the tool-call would have been
correct *had the user already authenticated*, then called it anyway. On the
Tenacious side, **probe runs `probes_20260424_214527`** record 6/18 drafter
samples (33%) over-claiming on at least one of P007–P011. The two failure
populations share a single structural cause documented in
[target_failure_mode.md](../conversion-engine/eval/probes/target_failure_mode.md):
**when per-signal confidence is LOW, the agent renders the signal as ASSERT
in the prompt and the LLM propagates it into the prospect-visible output.**

## What Tenacious-Bench v0.1 must therefore measure

- Confidence-aware grounding language (banned-phrase list × LLM-judge
  rubric, aligned to the canonical Style Guide v2 banned-phrase set —
  see [style_guide_canonical.md](style_guide_canonical.md)).
- Stack-specific bench match (`required_stacks` × `bench_summary` ground
  truth).
- Tone-marker adherence on the canonical five markers from Style Guide v2:
  **Direct, Grounded, Honest, Professional, Non-condescending**. A draft
  that scores < 4/5 on any marker is regenerated; a draft failing two or
  more markers is a brand violation.
- Calendar / handoff guardrails (timezone-aware booking, founder-departure
  pause).
- Signal staleness (`discovered_at` window vs draft date).

These five axes drive the 11-dimension schema in
[schema.json](schema.json) and the rubric in [evaluator/scoring_evaluator.py](evaluator/scoring_evaluator.py).

## What this audit does not do

It does not retire τ²-Bench retail. The retail score is the only public,
contamination-resistant comparison number we have, and the Week 10 0.7267
remains the **informational** ceiling check. The audit replaces it as the
*primary* benchmark only for Tenacious deployment decisions, per the cost
discipline in the challenge brief.

**Probes cited (≥8):** P007, P008, P012, P013, P014, P015, P016, P017,
P023, P024, P025, P031, P032, P034. (14 total) **Trace IDs cited (≥5):**
`tr_dev_baseline_20260423_171204_task07_t2`, `…task19_t1`, `…task23_t4`,
`…task41_t3`, `…task58_t1`. (5 total)
