# Canonical Tenacious Style Guide v2 — bench bindings

This file binds the Style Guide v2 (`ref/Technical Challenge/Tenacious Style
Guide and 12 Good-Bad Examples v2.docx`) to the Tenacious-Bench v0.1
schema and evaluator. Read alongside [schema.json](schema.json) and
[evaluator/scoring_evaluator.py](evaluator/scoring_evaluator.py).

## Five tone markers (canonical)

| Marker | Plain definition | Failing pattern | Bench enum |
|---|---|---|---|
| **Direct** | Clear, brief, actionable. Subject line states intent. Cold body ≤120 words; one ask. | "Quick", "Just", "Hey", multi-asks, filler openings | `direct` |
| **Grounded** | Every claim supported by hiring or competitor gap brief. Weak signal → ask, not assert. | "You're scaling aggressively" on 2 open roles | `grounded` |
| **Honest** | Refuses ungrounded claims. Names absences. Never over-commits bench or invents peer practices. | "World-class engineering team can plug in 6 MLEs" with no bench match | `honest` |
| **Professional** | Avoids internal jargon ("bench"), offshore clichés ("top talent", "rockstar"). | "Top talent A-players" in body | `professional` |
| **Non-condescending** | Frames gaps as findings or questions, not failures of the prospect's leadership. | "You clearly have not scoped MLOps" | `non_condescending` |

A draft scoring < 4/5 on any marker is regenerated; a draft failing two
or more markers is a brand violation.

## Canonical banned phrases (full list from Style Guide v2)

```
world-class
top talent
A-players
rockstar
ninja
wizard
skyrocket
supercharge
10x
I hope this email finds you well
just following up
circling back
Quick question
Quick chat
synergize
synergy
leverage
ecosystem
game-changer
disruptor
paradigm shift
our proprietary
our AI-powered
You'll regret missing this
Don't miss out
Per my last email
our 500 employees
our 20 years of experience
I'll keep this brief
I noticed you're a
```

These are merged into the per-task `rubric.banned_phrases` lists in
[`tenacious_bench_v0.1/`](tenacious_bench_v0.1/). Per-task lists also
include task-specific banned phrases (e.g., probe-derived "aggressive
hiring" for signal_overclaiming tasks).

## Formatting constraints (canonical)

| Constraint | Threshold | Bench encoding |
|---|---|---|
| Cold body word count | ≤ 120 | `rubric.structural.max_word_count` |
| Warm reply word count | ≤ 200 | `rubric.structural.max_word_count` |
| Re-engagement word count | ≤ 100 | `rubric.structural.max_word_count` |
| Subject line length | ≤ 60 chars | `rubric.structural.max_subject_chars` (v0.2) |
| One ask per body | exactly 1 | structural check (v0.2) |
| No PDF attachments in cold | enforced | structural check (v0.2) |
| No emojis in cold | enforced | regex check (v0.2) |

## Pre-flight checklist (canonical) → bench dimension mapping

| Pre-flight check | Bench dimension |
|---|---|
| Hiring signal grounding | `signal_overclaiming`, `gap_brief_overclaiming` |
| Confidence-aware phrasing | `signal_overclaiming` |
| Bench-vs-engineering-team language | `tone_marker_adherence` (Professional) |
| Bench-to-brief match | `bench_overcommitment` |
| Pricing scope | (v0.2) `pricing_overclaiming` |
| Word count | `tone_marker_adherence` (Direct), `cost_discipline` |
| One ask | `tone_marker_adherence` (Direct) |
| Banned phrase scan | `tone_marker_adherence` |
| LinkedIn-roast test | aggregate across all dimensions |

## Channel rules

Email is the default. LinkedIn DM permitted only for fresh leadership-change
signals (≤7 days), engaged prospects (last 14 days), or when email is
unavailable. SMS only after the prospect confirms. Voice = discovery call only,
booked through Cal.com, delivered by a human.

The bench scopes only the email channel for v0.1; channel-rule probes
move to v0.2 (one of the four named gaps in the Day-7 skeptic's appendix).

## v0.2 backlog created by reading Style Guide v2

1. **Subject-line check** — `max_subject_chars` and intent-prefix enum.
2. **One-ask enforcement** — exactly-one CTA detector beyond
   `single_call_to_action` heuristic.
3. **Pricing-band overclaiming** — new dimension for invented TCV / hourly
   rates outside `pricing_sheet.md` bands.
4. **Channel-rule grading** — LinkedIn DM and SMS pre-conditions.
