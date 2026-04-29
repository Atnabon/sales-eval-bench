# Synthesis Memo 02 — Datasheets for Datasets + Data Cards

> Gebru et al. (2021), *Datasheets for Datasets*, and Pushkarna et al.
> (FAccT 2022), *Data Cards: Purposeful and Transparent Dataset
> Documentation*. Reading status: completed 2026-04-21 night.

## What I take from both papers

Gebru gives the seven sections every datasheet must cover (motivation,
composition, collection, preprocessing, uses, distribution, maintenance).
Pushkarna extends this with a layered detail structure:

- **Telescopic** — the one-paragraph "what is this" that lets a reviewer
  decide whether to read further.
- **Periscopic** — the eight-section middle layer that maps onto Gebru.
- **Microscopic** — per-row, per-feature detail that lets a reviewer
  reproduce or audit one specific instance.

The two papers agree on motivation but disagree on the *audience model*.
Gebru's paper assumes a regulator-style reader who needs everything in one
document. Pushkarna assumes a multi-audience model — practitioners,
auditors, end users — and gives them three on-ramps.

## Where I disagree

**Claim under disagreement (Pushkarna §3):** the layered structure is
*always* better than a single flat document.

**My disagreement:** for a **small, deeply technical** dataset like
Tenacious-Bench (240 rows, 11 dimensions, 4 source modes), the layered
structure adds reading overhead without adding clarity. The audience for
this dataset is a narrow ML/agent-reliability practitioner who already
knows what an evaluation benchmark is. Three on-ramps over-design for
this audience.

**The compromise I made:** I kept Pushkarna's three layers
(telescopic / periscopic / microscopic) **as section headings**, but
collapsed them into a single document so a reviewer reads them in order
without navigating between files. The microscopic layer points back into
the per-task JSONL, which is itself the canonical microscopic detail.
Result: see [datasheet.md](../datasheet.md) — three sections, one
document, no inflation.

## Where Gebru is right and I am following exactly

**§5 (Uses):** explicit anti-uses are non-negotiable. I added two:

- Do not use Tenacious-Bench as a measure of general retail / customer
  service competence (that is τ²-Bench's job).
- Do not use the Tenacious style guide as a stand-in for any real
  company's brand voice — it is synthetic.

**§7 (Maintenance):** every release carries a CHANGELOG and a maintainer
contact. I will hold to this; if Tenacious-Bench picks up community
contributions, the maintenance log is what keeps the dataset honest.

## Where this changes Act V design

The blog post (Act V deliverable) needs a **telescopic-style opener**.
First 200 words must answer: what is the gap, what did I do about it, what
is the headline lift. That is what gets a reader past the fold on the HF
blog. Pushkarna's three-on-ramp model maps cleanly onto blog structure:
opener (telescopic) → middle sections (periscopic) → reproducibility
recipe (microscopic). I will not use a flat structure for the blog even
though I am using a flat structure for the datasheet.

## What I will not do

The papers also recommend a "responsible AI" boilerplate section. I am
**not** including this in v0.1. The dataset is built from public sources
and synthetic Tenacious materials; there is no PHI, no human subjects, no
demographic axes. A boilerplate section would be performative and add
length without adding signal. If a reviewer pushes back, I will add it
in v0.2 with concrete reasoning, not template text.

## Word count

~480 words.
