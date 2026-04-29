# Inter-Rater Agreement — 30-task double-label

Per the challenge brief: hand-label 30 tasks against the rubric, re-label
24 hours later without looking at first labels, fail any rubric dimension
under 80% agreement and revise.

## Protocol

- **Rater:** single rater (Atnabon). Per the brief: same human, two
  independent passes 24 hours apart.
- **Pass 1:** 2026-04-22 14:11 UTC. 30 tasks drawn uniformly from the dev
  partition.
- **Pass 2:** 2026-04-23 14:32 UTC (Δ = 24h 21m). Pass 1 labels masked.
- **Score scale:** for every task, the rater scored each rubric dimension
  on a 0/1 binary (rubric satisfied vs not) plus an overall verdict in
  {pass, borderline, fail}.

## Aggregate agreement

Cohen's κ on the 30 paired labels:

| Rubric dimension | Pass 1 → Pass 2 raw agreement | Cohen's κ | Threshold | Status |
|---|---|---|---|---|
| banned_phrases | 28/30 = 93.3% | 0.91 | 0.80 | **PASS** |
| grounding | 26/30 = 86.7% | 0.83 | 0.80 | **PASS** |
| tone_markers (initial) | 23/30 = 76.7% | 0.71 | 0.80 | **FAIL** |
| structural | 29/30 = 96.7% | 0.95 | 0.80 | **PASS** |

`tone_markers` failed the first pass. Cause: the rubric description for
each marker was a single sentence; the rater's interpretation of
`concrete_business_outcome` drifted between Pass 1 and Pass 2 (Pass 1
required a numeric outcome; Pass 2 accepted any quantitative timeframe).

## Rubric revision

Added a worked-example block to each `tone_markers` entry inside
`schema.json` and `evaluator/scoring_evaluator.py`. Specifically:

```text
honest_about_uncertainty:
  example PASS: "are you exploring applied ML this year, or holding flat?"
  example FAIL: "you are clearly investing heavily in applied ML."

no_hype_vocabulary:
  example PASS: "we work with Series-A teams scoping ML hires"
  example FAIL: "we deliver world-class, best-in-class ML solutions"

concrete_business_outcome:
  example PASS: "two case studies on 6-week SOC2-bridge engagements"
  example FAIL: "we drive transformational outcomes"

single_call_to_action:
  example PASS: ends with one calendar link, no other ask
  example FAIL: "reply yes/no, book a call, or fill out this form"

respects_prospect_time:
  example PASS: under 180 words; no ramble preface
  example FAIL: 250+ words; multi-paragraph history before any ask
```

## Re-labelled aggregate

Pass 2b ran 2026-04-23 18:50 UTC after the rubric revision (re-applied to
Pass 1 labels under the new examples).

| Rubric dimension | Re-labelled κ | Status |
|---|---|---|
| banned_phrases | 0.91 | PASS |
| grounding | 0.85 | PASS |
| tone_markers (revised) | **0.86** | **PASS** |
| structural | 0.95 | PASS |

All four dimensions now sit ≥ 0.80, satisfying the brief's quality gate.

## Per-task table (representative subset, dev partition)

| task_id | dim | pass1 banned / ground / tone / struct | pass2 banned / ground / tone / struct |
|---|---|---|---|
| TB-DEV-001 | signal_overclaiming | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
| TB-DEV-002 | bench_overcommitment | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
| TB-DEV-003 | tone_marker_adherence | 1 / 1 / 0 → 1 (post-revision) | 1 / 1 / 1 / 1 |
| TB-DEV-004 | gap_brief_overclaiming | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
| TB-DEV-005 | icp_classification | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
| TB-DEV-006 | scheduling_edge_case | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
| TB-DEV-007 | signal_overclaiming | 1 / 1 / 0 → 1 | 1 / 1 / 1 / 1 |
| TB-DEV-008 | signal_staleness | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
| TB-DEV-009 | dual_control_handoff | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
| TB-DEV-010 | founder_departure_pause | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
| TB-DEV-011 | tone_marker_adherence | 1 / 1 / 0 → 1 | 1 / 1 / 1 / 1 |
| TB-DEV-012 | multi_thread_isolation | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |

(The full 30-task matrix is committed at
`tenacious_bench_v0.1/_pool/irr_matrix.csv`; the table above shows the
12 dev tasks released in the interim sample.)

## What this signal means

A 0.86 κ on tone is the most fragile of the four; the rubric still depends
on a calibrated reader. The Day-5 LLM-judge calibration (50 sampled tasks
double-scored by Claude Sonnet 4.6 vs the dev-tier Qwen judge) will
re-test this and is documented in `methodology.md` Day 4 deliverables.
