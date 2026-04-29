# Judge Filter Prompt — Tenacious-Bench v0.1

> This file is the verbatim judge prompt used by `judge_filter.py` to apply
> pointwise quality scoring on each generated task before it enters the
> dataset. It is committed here so the scoring logic is auditable without
> reading Python source.
>
> **Model routing rule:** the judge model must be from a different family
> than the authoring model. Enforced by `pick_judge()` in `judge_filter.py`.
> See `model_routes.yaml` for the canonical family map.

---

## Prompt (sent verbatim to the judge model via OpenRouter)

```
Score the Tenacious-Bench task below on three dimensions, each 1–5.
Return JSON only — no explanation, no markdown fences.

Scoring dimensions:
  input_coherence              (1–5): Is the task input logically consistent
                                      and unambiguous? Does the instruction
                                      match the brief fields provided?
                                      5 = fully coherent; 1 = contradictory or
                                      missing essential fields.

  ground_truth_verifiability   (1–5): Can a competent evaluator determine
                                      whether an agent response satisfies the
                                      rubric without subjective judgment?
                                      5 = fully mechanical; 1 = requires expert
                                      opinion with no rubric anchor.

  rubric_application_clarity   (1–5): Are the rubric components (banned_phrases,
                                      required_grounding, tone_markers, structural)
                                      complete, specific, and independently
                                      applicable?
                                      5 = every rubric element is independently
                                      checkable; 1 = rubric is vague, circular,
                                      or references undefined terms.

Threshold: all three scores must be ≥ 4 for the task to be accepted.

Task (JSON):
{task_json_truncated_to_6000_chars}

Return format:
{"input_coherence": <int>, "ground_truth_verifiability": <int>, "rubric_application_clarity": <int>}
```

---

## Calibration examples

### input_coherence

| Score | Meaning | Example trigger |
|---|---|---|
| 5 | Instruction fully supported by brief fields | `instruction: "Draft email for Series A company"` + `funding.round: "Series A"` present |
| 3 | Minor ambiguity — instruction implies a field not in the brief | `instruction: "Reference the bench"` but no `bench_summary` provided |
| 1 | Contradiction — instruction contradicts brief | `instruction: "Do not mention funding"` + `required_grounding` requires funding fact |

### ground_truth_verifiability

| Score | Meaning | Example trigger |
|---|---|---|
| 5 | `expected_action` is deterministic; `reference_chosen` resolves all rubric items | `expected_action: "abstain"` — binary, no subjective judgment |
| 3 | `expected_action` present but `reference_chosen` absent for a "draft_email" task | Evaluator must infer a passing email with no canonical reference |
| 1 | Rubric references external documents not in the task schema | `"must comply with brand voice guidelines"` with no guidelines attached |

### rubric_application_clarity

| Score | Meaning | Example trigger |
|---|---|---|
| 5 | All rubric components populated; each item is independently checkable | `banned_phrases` non-empty list + `structural.max_word_count` set + tone markers named |
| 3 | One rubric component is vague or empty | `tone_markers: []` — no markers to check against |
| 1 | Rubric items use undefined terms or are circular | `banned_phrases: ["unprofessional language"]` — requires subjective judgment to apply |

---

## Pairwise tiebreak prompt

When two synthesis paths produce near-duplicate tasks (Jaccard ≥ 0.20),
the following pairwise prompt selects the more diagnostic one:

```
Two tasks are near-duplicates (n-gram Jaccard ≥ 0.20). Select the one that
better discriminates between a passing and a failing agent response.
"Better" means: (a) the failure mode is harder to avoid by chance, and
(b) the rubric cannot be gamed by a simple heuristic (e.g., just avoiding
one keyword).

Task A: {task_a_json}
Task B: {task_b_json}

Return JSON: {"winner": "A" or "B", "reason": "<one sentence>"}
```
