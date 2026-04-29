"""Tenacious-Bench v0.1 scoring evaluator.

Reads a task plus a candidate output and returns a numerical score with no
human in the loop. Four rubric components are combined under documented
weights:

    banned_phrases   30%   deterministic substring/regex match
    grounding        30%   deterministic fact-presence + ASK-not-ASSERT check
    tone             25%   5 style-guide markers, LLM-judge scored 1-5
    structural       15%   deterministic structural guardrails

The LLM-judge tier is dev-tier by default (Qwen3-Next via OpenRouter); pass
``--judge eval`` to switch to Claude Sonnet 4.6 for the sealed held-out only.

Usage:
    python evaluator/scoring_evaluator.py \\
        --task tenacious_bench_v0.1/dev/tasks.jsonl#TB-DEV-007 \\
        --candidate path/to/candidate.txt

Outputs a JSON document on stdout. Returns exit code 0 on success, 2 on
schema validation error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_WEIGHTS = {
    "banned_phrases": 0.30,
    "grounding": 0.30,
    "tone": 0.25,
    "structural": 0.15,
}

# ---------------------------------------------------------------------------
# Score calibration guide (what raw 0.0 / 0.5 / 1.0 means per dimension)
# ---------------------------------------------------------------------------
# banned_phrases  raw=1.0  → zero hits from the task's banned-phrase list
#                 raw=0.75 → one hit (−0.25 per hit, floored at 0)
#                 raw=0.5  → two hits
#                 raw=0.0  → four or more hits
#
# grounding       raw=1.0  → all required_grounding facts present and, where
#                            must_be_asked_not_asserted_when_low_confidence=True
#                            and confidence is LOW, rendered as a question
#                 raw=0.5  → half of required facts satisfied (e.g. 1/2)
#                 raw=0.0  → no required facts present in candidate
#
# tone            raw=1.0  → LLM judge scores every marker 5/5
#  (LLM 1-5)      raw=0.6  → markers average 3/5 (acceptable but not polished)
#                 raw=0.0  → all markers score 1/5 (systematic style violations)
#
# structural      raw=1.0  → all structural checks pass
#  (deterministic) raw=0.5  → half of checks pass (e.g. calendar link present
#                             but word count exceeded)
#                 raw=0.0  → all checks fail (no calendar link, word cap blown,
#                             founder-departure not paused when required)
# ---------------------------------------------------------------------------


# ----------------------------------------------------------------------------
# Task loading
# ----------------------------------------------------------------------------


def load_task(task_ref: str) -> dict[str, Any]:
    """Resolve "path/to.jsonl#TB-DEV-007" or a bare path."""
    if "#" in task_ref:
        path_str, task_id = task_ref.split("#", 1)
    else:
        path_str, task_id = task_ref, None
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if task_id is None or row["task_id"] == task_id:
                return row
    raise KeyError(f"task_id={task_id} not found in {path}")


def load_candidate(candidate_ref: str) -> str:
    p = Path(candidate_ref)
    if p.exists():
        return p.read_text()
    return candidate_ref  # treat as inline string


# ----------------------------------------------------------------------------
# Scoring components
# ----------------------------------------------------------------------------


@dataclass
class ComponentScore:
    name: str
    raw: float       # 0.0 - 1.0
    detail: dict[str, Any]


def score_banned_phrases(rubric: dict, candidate: str) -> ComponentScore:
    banned = rubric.get("banned_phrases", []) or []
    hits: list[str] = []
    lc = candidate.lower()
    for phrase in banned:
        if phrase.lower() in lc:
            hits.append(phrase)
    raw = 1.0 if not hits else max(0.0, 1.0 - 0.25 * len(hits))
    return ComponentScore("banned_phrases", raw, {"hits": hits, "total_banned": len(banned)})


def score_grounding(rubric: dict, task_input: dict, candidate: str) -> ComponentScore:
    """Each `required_grounding` entry must:
      (a) appear in the candidate (substring or normalized number); and
      (b) when LOW confidence + must_be_asked_not_asserted_when_low_confidence
          is True, appear in interrogative form ("are you exploring …?")
          rather than ASSERT form ("you are doing aggressive hiring").
    """
    reqs = rubric.get("required_grounding", []) or []
    if not reqs:
        return ComponentScore("grounding", 1.0, {"reqs": 0})

    lc = candidate.lower()
    issues: list[dict] = []
    hits = 0

    # Build a confidence map from the input shape so we can check ASK-not-ASSERT
    confidence_map = _flatten_confidence(task_input)

    for req in reqs:
        key = req["fact_key"]
        expected = str(req["expected_value"]).lower()
        must_ask = req.get("must_be_asked_not_asserted_when_low_confidence", False)
        present = expected in lc
        if not present:
            issues.append({"fact_key": key, "issue": "missing"})
            continue
        if must_ask and confidence_map.get(key) == "LOW":
            asserted = _looks_asserted(candidate, expected)
            if asserted:
                issues.append({"fact_key": key, "issue": "asserted_on_LOW_confidence"})
                continue
        hits += 1

    raw = hits / len(reqs)
    return ComponentScore("grounding", raw, {"hits": hits, "total": len(reqs), "issues": issues})


def _flatten_confidence(task_input: dict) -> dict[str, str]:
    """Walk the brief shapes and surface fact_key -> confidence."""
    out: dict[str, str] = {}
    brief = task_input.get("hiring_signal_brief") or {}
    for k in ("ai_maturity", "funding", "hiring"):
        if isinstance(brief.get(k), dict) and "confidence" in brief[k]:
            out[k] = brief[k]["confidence"]
            for sub in ("score", "amount_usd", "open_eng_roles", "ai_adjacent_eng_roles"):
                if sub in brief[k]:
                    out[f"{k}.{sub}"] = brief[k]["confidence"]
    gaps = (task_input.get("competitor_gap_brief") or {}).get("gaps", []) or []
    for i, gap in enumerate(gaps):
        if "confidence" in gap:
            out[f"competitor_gap.{i}"] = gap["confidence"]
            out[f"competitor_gap.{i}.claim"] = gap["confidence"]
    return out


_ASSERT_PATTERNS = [
    r"\byou are\b",
    r"\byou're\b",
    r"\byour team is\b",
    r"\bgiven your\b",
    r"\bsince you\b",
    r"\baggressive\b",
    r"\bclearly\b",
]
_ASSERT_RE = re.compile("|".join(_ASSERT_PATTERNS), re.IGNORECASE)


def _looks_asserted(candidate: str, fact_substr: str) -> bool:
    """Heuristic: is the fact rendered as ASSERT (statement) rather than ASK
    (question) within +/- 80 chars of the fact mention?"""
    lc = candidate.lower()
    idx = lc.find(fact_substr.lower())
    if idx < 0:
        return False
    window = candidate[max(0, idx - 80): idx + len(fact_substr) + 80]
    if "?" in window:
        return False
    return bool(_ASSERT_RE.search(window))


def score_structural(rubric: dict, task_input: dict, candidate: str) -> ComponentScore:
    s = rubric.get("structural", {}) or {}
    issues: list[str] = []
    checks = 0
    passes = 0

    if s.get("must_end_with_calendar_link_or_handoff"):
        checks += 1
        if re.search(r"(calendly|cal\.com|/book|hand[\s-]?off|hubspot)", candidate, re.IGNORECASE):
            passes += 1
        else:
            issues.append("missing_calendar_or_handoff")

    if s.get("must_omit_proposed_times_when_timezone_null"):
        checks += 1
        prospect = task_input.get("prospect") or {}
        if prospect.get("timezone") is None and re.search(
            r"\b(?:\d{1,2}(?::\d{2})?\s?(?:am|pm)|tomorrow at|tuesday at)\b",
            candidate, re.IGNORECASE,
        ):
            issues.append("proposed_local_time_with_no_timezone")
        else:
            passes += 1

    if "max_word_count" in s:
        checks += 1
        wc = len(candidate.split())
        if wc <= s["max_word_count"]:
            passes += 1
        else:
            issues.append(f"word_count_{wc}_over_{s['max_word_count']}")

    if s.get("must_pause_on_founder_departure"):
        checks += 1
        leadership = ((task_input.get("hiring_signal_brief") or {})
                      .get("leadership") or {})
        is_founder = leadership.get("role", "").lower() == "founder"
        if is_founder and not re.search(r"(pause|hold|revisit later|circle back)", candidate, re.IGNORECASE):
            issues.append("founder_departure_not_paused")
        else:
            passes += 1

    raw = 1.0 if checks == 0 else passes / checks
    return ComponentScore("structural", raw, {"checks": checks, "passes": passes, "issues": issues})


# ----------------------------------------------------------------------------
# Tone — LLM judge (dev-tier by default)
# ----------------------------------------------------------------------------


def score_tone(rubric: dict, candidate: str, judge: str) -> ComponentScore:
    markers = rubric.get("tone_markers", []) or []
    if not markers:
        return ComponentScore("tone", 1.0, {"markers": 0})

    if judge == "eval":
        model = "anthropic/claude-sonnet-4.6"
    elif judge == "dev":
        model = "qwen/qwen3-next-80b-a3b"
    else:
        # offline mode: deterministic stub (used in CI / smoke tests)
        return _score_tone_offline(markers, candidate)

    try:
        scores = _llm_judge_call(model, markers, candidate)
    except Exception as exc:  # pragma: no cover — offline fallback
        return _score_tone_offline(markers, candidate, error=str(exc))

    raw = sum(scores.values()) / (5 * len(scores))
    return ComponentScore("tone", raw, {"per_marker": scores, "judge": model})


def _score_tone_offline(markers: list[str], candidate: str, error: str | None = None) -> ComponentScore:
    """Heuristic stub used when no judge API is reachable. Each marker gets
    a crude 1-5 score by pattern, aligned to the canonical Style Guide v2
    markers (Direct, Grounded, Honest, Professional, Non-condescending).
    Documented in methodology.md as the offline fallback for CI."""
    HYPE = {
        "world-class", "top talent", "a-players", "rockstar", "ninja", "wizard",
        "skyrocket", "supercharge", "10x", "synergize", "synergy", "ecosystem",
        "game-changer", "disruptor", "paradigm shift", "leverage",
        "our proprietary", "our ai-powered",
    }
    INTERNAL_JARGON = {"bench", "off-the-bench", "leverage our bench"}
    HEDGE = ("might", "may", "could", "are you", "if you", "is hiring")
    CONDESCEND = (
        "you clearly", "you're behind", "you obviously", "you don't have",
        "you lack", "your team is failing",
    )
    out: dict[str, int] = {}
    lc = candidate.lower()
    for marker in markers:
        if marker == "direct":
            wc = len(candidate.split())
            ctas = len(re.findall(r"(book|schedule|reply|let me know|grab a slot|calendar)", lc))
            out[marker] = 5 if (wc <= 120 and ctas == 1) else (4 if wc <= 200 and ctas == 1 else 2)
        elif marker == "grounded":
            specific = bool(re.search(r"\b(series\s?[abc]|seed|pre-seed|\$[\d,]+|\d+\s?(open|engineers?|roles?|hires?))\b", lc))
            out[marker] = 5 if specific else 2
        elif marker == "honest":
            asserts = bool(re.search(r"\b(aggressive hiring|clearly scaling|you are clearly|you're clearly|given your funding)\b", lc))
            asks = any(h in lc for h in HEDGE)
            out[marker] = 5 if (asks and not asserts) else (2 if asserts else 4)
        elif marker == "professional":
            jargon_hit = any(j in lc for j in INTERNAL_JARGON) or any(h in lc for h in HYPE)
            out[marker] = 1 if jargon_hit else 5
        elif marker == "non_condescending":
            condescend_hit = any(c in lc for c in CONDESCEND)
            out[marker] = 1 if condescend_hit else 5
        # legacy markers kept for backwards-compatibility with v0.1.0-interim tasks
        elif marker == "honest_about_uncertainty":
            out[marker] = 5 if any(h in lc for h in HEDGE) else 3
        elif marker == "no_hype_vocabulary":
            out[marker] = 5 if not any(w in lc for w in HYPE) else 2
        elif marker == "single_call_to_action":
            ctas = len(re.findall(r"(book|schedule|reply|let me know|grab a slot)", lc))
            out[marker] = 5 if ctas == 1 else (3 if ctas == 0 else 2)
        elif marker == "concrete_business_outcome":
            out[marker] = 5 if re.search(r"\b\d+\s?(weeks?|days?|hires?|engineers?|%)\b", candidate) else 3
        elif marker == "respects_prospect_time":
            out[marker] = 5 if len(candidate.split()) < 180 else 3
        else:
            out[marker] = 3
    raw = sum(out.values()) / (5 * len(out))
    return ComponentScore("tone", raw, {"per_marker": out, "judge": "offline_stub", "error": error})


def _llm_judge_call(model: str, markers: list[str], candidate: str) -> dict[str, int]:
    """Real OpenRouter call. Kept as a single function so tests can monkey-patch."""
    import httpx
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    prompt = (
        "You are grading a B2B outreach email against the Tenacious style guide.\n"
        "For each marker below, output an integer 1-5 (5 = fully satisfies the marker, "
        "1 = strongly violates). Output JSON with marker keys.\n\n"
        f"Markers: {markers}\n\nEmail:\n{candidate}\n\nJSON only:"
    )
    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0},
        timeout=60.0,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    parsed = json.loads(re.search(r"\{.*\}", text, re.DOTALL).group(0))
    return {m: int(parsed[m]) for m in markers if m in parsed}


# ----------------------------------------------------------------------------
# Composite
# ----------------------------------------------------------------------------


def evaluate(task: dict, candidate: str, judge: str = "offline") -> dict:
    rubric = task["rubric"]
    weights = {**DEFAULT_WEIGHTS, **(rubric.get("scoring_weights") or {})}

    components = [
        score_banned_phrases(rubric, candidate),
        score_grounding(rubric, task["input"], candidate),
        score_tone(rubric, candidate, judge),
        score_structural(rubric, task["input"], candidate),
    ]
    total = sum(weights[c.name] * c.raw for c in components)
    verdict = _verdict(components, total)
    return {
        "task_id": task["task_id"],
        "score_total": round(total, 4),
        "weights": weights,
        "rubric_breakdown": {c.name: {"raw": round(c.raw, 4), **c.detail} for c in components},
        "verdict": verdict,
    }


def _verdict(components: list[ComponentScore], total: float) -> str:
    by_name = {c.name: c.raw for c in components}
    if by_name.get("banned_phrases", 1.0) < 1.0:
        return "tone_violation"
    if by_name.get("grounding", 1.0) < 0.7:
        return "weak_grounding"
    if by_name.get("structural", 1.0) < 0.7:
        return "structural_failure"
    if total >= 0.85:
        return "pass"
    return "borderline"


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="path.jsonl#TASK_ID")
    parser.add_argument("--candidate", required=True, help="path or inline string")
    parser.add_argument("--judge", default="offline", choices=["offline", "dev", "eval"])
    args = parser.parse_args(argv)

    task = load_task(args.task)
    candidate = load_candidate(args.candidate)
    result = evaluate(task, candidate, judge=args.judge)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
