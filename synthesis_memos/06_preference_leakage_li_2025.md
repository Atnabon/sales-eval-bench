# Synthesis Memo — *Preference Leakage: A Contamination Problem in LLM-as-a-Judge* (Li et al., 2025)

> **Path-B-specific reading.** This paper directly governs the routing
> rules in `generation_scripts/model_routes.yaml` and the anti-leakage
> invariant in `training_data/build_preference_pairs.py`.

## What the paper claims

Li et al. demonstrate a measurable accuracy / preference inflation when
the same LLM is used to *generate* preference pairs and to *judge* them.
Across five benchmark suites, the same-family generate-and-judge pipeline
inflated reported preference accuracy by 4–11 percentage points relative
to a held-out human-judged ground truth. The mechanism is straightforward:
a model's tokenisation and reasoning patterns are stable across calls, so
the chosen output and the judge's preferred output share spurious
features the human grader does not.

The paper's recommendation — the rotation rule — is that the model that
generates a chosen-rejected pair must come from a *different family* than
the model that judges that same pair. Family is defined at the
pre-training-corpus level, so swapping between Claude-Haiku and
Claude-Sonnet does not satisfy the rule; swapping between
Claude-Sonnet and Qwen does.

## What I am taking from it

The whole anti-leakage architecture in our pipeline. Concretely:

1. **At generation time.** `generation_scripts/judge_filter.py:pick_judge`
   takes the authoring family as input and refuses to return a judge
   from the same family. The family map lives in
   `model_routes.yaml#leakage_prevention.family_map`.

2. **At preference-pair construction time.**
   `training_data/build_preference_pairs.py` enforces
   `chosen_source_family != rejected_source_family` in the
   `PreferencePair.as_row()` assertion — a row that fails the invariant
   is not just dropped, the harness raises `AssertionError`. This is
   deliberately strict because a silent leakage drop would pollute the
   training set and the lift number would be misleading without the
   pipeline visibly refusing to produce it.

3. **At evaluation time.** Eval-tier sealed-slice scoring uses Claude
   Sonnet 4.6 (`anthropic`); training data preference pairs use
   `deepseek` for chosen rewrites and `anthropic` for rejected drafts.
   The eval-tier judge therefore shares the rejected family but **not**
   the chosen family — which is the asymmetric form of the rule that
   matters: the judge must not match the *winning* side.

## Where I disagree

The paper treats family as the right granularity for the rotation rule.
Two reasons I think family is necessary but not sufficient:

1. **Shared training corpora across families.** Modern open-weight
   models increasingly train on overlapping public corpora (Common Crawl,
   FineWeb, public-domain text). Two "different family" models can
   share 60–80 % of their pre-training distribution. The paper's
   experimental design uses families that were trained on more disjoint
   data than current open-weight families typically are. Our deepseek
   ↔ qwen pair is closer to "same family" by this stricter standard
   than the paper's claude ↔ llama pair.

2. **Preference shape, not just text.** Even across families, models
   trained with similar RLHF recipes produce structurally similar
   preferences (e.g., they both reward "concise, polite, ends with a
   call to action"). The leakage the paper measures is *lexical*; the
   leakage we should worry about for a sales judge is *stylistic*. The
   paper's family-rotation rule does not address stylistic leakage.

For our work, this is a known v0.2 concern. We document it in the model
card §5 and in the FINAL_REPORT.md skeptic's appendix as a
"public-signal lossiness" issue extended to "model-family lossiness."

## Operational consequence for our work

- Family-rotation rule enforced as the paper recommends.
- We additionally instrument the judge-filter logs to record the *style
  metric distribution* of chosen vs. rejected drafts and flag any pair
  where the structural style overlap exceeds a threshold. (Implemented
  as a `style_signature` field in v0.2; not committed for v0.1.)
- The kill-switch trigger in FINAL_REPORT.md includes a check on
  judge-pass-rate decay — if the production judge starts passing every
  draft, leakage in the training set is one of the diagnoses we will
  test.
