# Tenacious-Bench v0.1 — Sales Agent Evaluation Bench

> **Week 11 / TRP1 Ground Truth.** Builds the Tenacious-specific evaluation
> dataset, scoring evaluator, and a small trained component (Path B — judge)
> that lifts the Week 10 Conversion Engine on a Tenacious-specific failure
> mode: **signal over-claiming**.

## Status

- **Phase:** Interim submission (Acts I–II of the five-act loop).
- **Path:** **B** — preference-tuned judge / critic (SimPO).
- **Backbone (planned for Act IV):** `Qwen/Qwen3.5-2B`.
- **Held-out:** sealed; not committed to public repo in plaintext (see
  `tenacious_bench_v0.1/held_out/SEALED.md`).
- **Dataset version:** `v0.1.0-interim` — 240 tasks across 11 dimensions.

## What is here (interim)

```
sales-eval-bench/
├── README.md                          # this file
├── INTERIM_REPORT.md                  # Google-Doc-format interim report (Mermaid diagrams)
├── audit_memo.md                      # Act I — 600-word audit
├── schema.json                        # Tenacious-Bench v0.1 task schema
├── methodology.md                     # path declaration, partitioning, contamination, IRR
├── datasheet.md                       # Gebru §1–§7 + Pushkarna telescopic/periscopic/microscopic
├── inter_rater_agreement.md           # 30-task double-label IRR matrix
├── cost_log.md                        # every API + compute charge
├── evaluator/
│   └── scoring_evaluator.py           # machine-verifiable scorer (no human in the loop)
├── tenacious_bench_v0.1/
│   ├── manifest.json                  # version, partition counts, license
│   ├── contamination_check.json       # n-gram + embedding + time-shift report
│   ├── train/tasks.jsonl              # 50% (120 tasks)
│   ├── dev/tasks.jsonl                # 30%  (72 tasks)
│   └── held_out/                      # 20%  (48 tasks) — sealed
│       ├── SEALED.md
│       └── tasks.encrypted.placeholder
├── generation_scripts/
│   ├── model_routes.yaml              # synthesis-LLM router config
│   ├── trace_to_task.py               # mode 1 — Week 10 trace → task
│   ├── programmatic_sweep.py          # mode 2 — template + slot expansion
│   ├── multi_llm_synthesis.py         # mode 3 — frontier seed → cheap variant
│   ├── hand_authored_seeds.jsonl      # mode 4 — adversarial hand-authored
│   ├── judge_filter.py                # 3-dim pointwise judge + pairwise tiebreak
│   ├── dedup.py                       # n-gram + embedding dedup
│   └── README.md                      # how to re-run authoring end-to-end
└── synthesis_memos/
    ├── 01_synthetic_data_liu_2024.md  # Liu et al., COLM 2024
    └── 02_datasheets_data_cards.md    # Gebru 2021 + Pushkarna 2022
```

## Setup

```bash
cd sales-eval-bench
python -m venv .venv && source .venv/bin/activate
pip install -r ../conversion-engine/requirements.txt   # reuse Week 10 deps
pip install datasets sentence-transformers rapidfuzz pyyaml
export OPENROUTER_API_KEY=...    # required for generation_scripts/*
export HUGGINGFACE_TOKEN=...     # required for Act V dataset push
```

## Quickstart — score one Week 10 draft against the bench

```bash
python evaluator/scoring_evaluator.py \
  --task tenacious_bench_v0.1/dev/tasks.jsonl#TB-DEV-007 \
  --candidate ../conversion-engine/outputs/sample_email_007.txt
# → {"score_total": 0.71, "rubric_breakdown": {...}, "verdict": "weak_grounding"}
```

## What is next (final submission, Acts III–V)

- **Day 4:** convert `train/` partition into SimPO `(chosen, rejected)`
  preference pairs. Source `rejected` from 12 SCAP-triggering Week 10 draft
  failures; `chosen` rewrites by a different model family (preference-leakage
  prevention per Li et al., 2025).
- **Day 5:** SimPO-tune a Qwen 3.5 2B judge head on Unsloth / Colab T4. ~45–60
  min wall, $0 compute target.
- **Day 6:** Delta A / Delta B / Delta C ablations on sealed held-out.
- **Day 7:** publish HF dataset, HF model adapter, blog post (1.2–2k words),
  GitHub issue on the τ²-Bench repo, two-page CEO/CFO memo.

## License

`tenacious_bench_v0.1/` released under **CC-BY-4.0** (datasheet rationale
in [methodology.md](methodology.md#license)). Code under MIT.

## Provenance

Built from the Week 10 Conversion Engine artifacts at
[../conversion-engine/](../conversion-engine/) — 1,622-line `trace_log.jsonl`,
37-probe library, 11-category failure taxonomy. Every numeric claim in the
interim report resolves to a task ID, a probe ID, or a trace ID; see
`evidence_graph.json` (Act V).
