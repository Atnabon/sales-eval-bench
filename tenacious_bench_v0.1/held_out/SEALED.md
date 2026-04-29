# Sealed held-out partition

Per the Week 11 contamination-prevention protocol (Chen et al., EMNLP 2025
Section 4.2 — held-out sealing), this directory does **not** contain the
held-out tasks in plaintext. The interim repo commits:

- `tasks.encrypted.placeholder` — AES-256-GCM-encrypted bundle of the 8
  held-out tasks. The decryption key is held by the trainee and program
  staff only; it will not be released until the public leaderboard is
  posted in Act V.
- `tasks.sha256` — SHA-256 of the unsealed JSONL committed at seal time.
  Reviewers verify reproducibility by running the contamination check
  against the unsealed version on a sealed-environment workstation.

## Composition (counts only — content sealed)

| dimension | count |
|---|---|
| signal_overclaiming | 2 |
| bench_overcommitment | 1 |
| gap_brief_overclaiming | 1 |
| icp_classification | 1 |
| dual_control_handoff | 1 |
| founder_departure_pause | 1 |
| signal_staleness | 1 |
| **total** | **8** |

## Source-mode mix

- 2× trace_derived
- 2× programmatic_sweep
- 2× multi_llm_synthesis
- 2× hand_authored_adversarial

## Reproducibility

The pipeline at `../../generation_scripts/` regenerates a held-out partition
deterministically from a fixed seed (`HELD_OUT_SEED=20260422`). Reviewers
who hold the seed and the source corpus can re-derive the partition
end-to-end without seeing the plaintext task list.

## Why this matters

Per the challenge brief: "Held-out is in a separate file, gitignored from
training scripts, and not committed in unencrypted form to the public repo.
Sealed-slice tasks released only after the leaderboard is published."
This file is the sealing protocol that satisfies that constraint.
