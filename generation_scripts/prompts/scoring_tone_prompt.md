# Tone-Judge Prompt — Tenacious-Bench v0.1 Scoring Evaluator

> This file is the verbatim tone-judge prompt used by
> `evaluator/scoring_evaluator.py` when `--judge dev` or `--judge eval` is
> passed. It is committed here so the scoring criteria are auditable without
> reading Python source.
>
> **Model routing:** `--judge dev` routes to `qwen/qwen3-next-80b-a3b` via
> OpenRouter (used during authoring iteration). `--judge eval` routes to
> `anthropic/claude-sonnet-4.6` and is reserved for the sealed held-out
> partition only.

---

## Prompt (sent verbatim to the judge model via OpenRouter)

```
You are grading a B2B outreach email against the Tenacious style guide.

For each marker below, output an integer 1–5 where:
  5 = the email fully satisfies this marker
  4 = satisfies with minor lapses
  3 = neutral / ambiguous
  2 = partially violates
  1 = clearly violates

Output JSON with marker names as keys. No explanation, no markdown.

Markers: {markers_list}

Email to grade:
{candidate_email}

JSON only:
```

---

## Marker definitions and calibration

### direct

The email is brief, unambiguous, and contains exactly one call to action.

| Score | Example |
|---|---|
| 5 | ≤ 120 words, single calendar link, no embedded questions or sub-asks |
| 4 | 120–160 words, one clear CTA, one minor rhetorical flourish |
| 3 | 160–200 words or two asks that are arguably the same intent |
| 2 | 200+ words or two clearly distinct calls to action |
| 1 | Wall of text, no clear CTA, or three or more separate asks |

### grounded

The email references specific, verifiable signal from the brief.

| Score | Example |
|---|---|
| 5 | Cites the exact funding round and at least one hiring detail from the brief |
| 4 | Cites the funding round; hiring detail is gestural but not fabricated |
| 3 | Vague reference to "your recent growth" without naming the signal |
| 2 | References a signal not present in the brief |
| 1 | Fabricates or directly contradicts brief data |

### honest

The email does not overstate certainty; LOW-confidence signals appear as
questions or conditionals, not assertions.

| Score | Example |
|---|---|
| 5 | All LOW-confidence signals framed as "are you…?", "if you're…", "I noticed…" |
| 4 | One minor assert on a MEDIUM-confidence signal |
| 3 | One mild assert on a LOW-confidence signal but not the core claim |
| 2 | Core claim asserted on LOW-confidence signal with hedging elsewhere |
| 1 | "You're clearly scaling fast" / "you're aggressively hiring" on LOW data |

### professional

The email uses Tenacious-appropriate vocabulary. No hype, no internal
jargon ("bench", "off-the-bench", "leverage our bench"), no superlatives.

| Score | Example |
|---|---|
| 5 | Specific, plain language; no terms from the banned-phrase list |
| 4 | One borderline word (e.g., "excited") that is not on the list |
| 3 | One soft hype word that is adjacent to the banned list |
| 2 | One explicit banned phrase (e.g., "world-class") |
| 1 | Multiple banned phrases or internal jargon ("bench-strength", "leverage our bench") |

### non_condescending

The email does not imply the prospect is behind, lacking, or failing.

| Score | Example |
|---|---|
| 5 | Entirely neutral framing; prospect's current state is not judged |
| 4 | One mildly presumptuous phrase ("I imagine you're…") |
| 3 | Framing slightly assumes a problem the prospect hasn't confirmed |
| 2 | Implicit condescension ("you may not have considered…") |
| 1 | Explicit condescension ("you're behind", "you obviously lack", "your team is failing") |
