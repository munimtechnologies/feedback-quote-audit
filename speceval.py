# Copyright 2026 Munim, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""speceval: does feedback ranked more specific quote the student's own words more faithfully? (audit 5)

Part of feedback-quote-audit, by MV2 of Munim, Inc. Made with AI agents working in his name.

Audits 1-3 checked GLM-4.7 on IELTS essays; audit 4 checked six LLMs on SEFORA university essays.
This pass, fixed in PLAN-5.md before it ran, applies the same quote filters and classes (it imports
audit.py and explain.py) to SpecEval, the specificity preference set released with FeedEval (Chu,
Kim and Yi, ACL Findings 2026): LLM feedback on ASAP++ student essays in chosen/rejected pairs,
ranked by a specificity score that counts the essay passages the feedback quotes. Each distinct
feedback text is checked once and ranked top (only ever chosen), bottom (only ever rejected) or
middle. It asks whether quotes keep the student's words, whether short quotes change words more
than long ones, and whether top-ranked feedback quotes any more faithfully than bottom-ranked.
The file is read in memory; only aggregate counts are written, no essay or feedback text.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

import audit
import explain
import verbatim_quote_check as vqc

DRIVE_ID = "1G71f7CFVLVV2cx908Du8jGW6k2Y0OhcF"  # speceval_dataset.json in FeedEval's Drive folder
SHA256 = "3d7e88527155194cbf597a9de75ee06d45b79871a68a06bbb6ab04f089bd996b"  # schema probe, 2026-10-30
TIGHT = 0.8  # best-match similarity at or above which a changed quote is a close (tight) copy
SHORT = (4, 6)  # quote length in words, inclusive, for the short stratum
LONG_MIN = 11  # long stratum: 11 words or more (audits 3-4)
RANKS = ("top", "middle", "bottom")
KEYS = ("feedback", "feedback_quoting", "feedback_with_wc", "quotes", "excluded_cue", "under_min_words",
        "not_found", "n", "wc", "prim_tight", "wc_tight", "wc_loose", "n_short", "wc_short", "n_long", "wc_long")
# name: (numerator key, denominator key)
RATES = {"word_changed_rate": ("wc", "n"),
         "loose_share_of_changed": ("wc_loose", "wc"),
         "quoting_feedback_share": ("feedback_quoting", "feedback"),
         "feedback_with_changed_share": ("feedback_with_wc", "feedback"),
         "primary_quotes_per_feedback": ("n", "feedback")}

REPS = 10_000
SEED = "feedback-quote-audit-5-20261030"
FLOOR = 300  # primary-set quotes needed for the pooled verdict (E1)
GROUP_FLOOR = 100  # quotes needed in each side of a comparison (E2, E3)
WC_MAX = 0.05  # E1 holds if the pooled word-changed rate is at most this (audit 1b's P3 bound)
MARGIN = 0.01  # E3 holds if top minus bottom is credibly above -MARGIN


def rank(chosen: int, rejected: int) -> str:
    """top = only ever the chosen side of a pair; bottom = only ever the rejected side; else middle."""
    if chosen and not rejected:
        return "top"
    if rejected and not chosen:
        return "bottom"
    return "middle"


def collect(records) -> tuple[dict, dict]:
    """Distinct feedback per essay {essay_id: {"set", "essay", "feedback": {text: [chosen, rejected]}}}, and counts."""
    essays: dict = {}
    info: dict = {"records": 0, "skipped_records": 0, "essay_text_conflicts": 0, "splits": {}}
    for rec in records:
        info["records"] += 1
        if not isinstance(rec, dict) or not isinstance(rec.get("essay"), str) or not rec["essay"].strip():
            info["skipped_records"] += 1
            continue
        split = str(rec.get("split"))
        info["splits"][split] = info["splits"].get(split, 0) + 1
        e = essays.setdefault(str(rec.get("essay_id")),
                              {"set": str(rec.get("essay_set")), "essay": rec["essay"], "feedback": {}})
        if e["essay"] != rec["essay"]:
            info["essay_text_conflicts"] += 1
        for j, side in enumerate(("chosen", "rejected")):
            text = rec.get(side)
            if isinstance(text, str) and text.strip():
                e["feedback"].setdefault(text, [0, 0])[j] += 1
    return essays, info


def tally(c: dict, quote: str, rec: dict, eforms: list[str], essay_words: list[str]) -> tuple[bool, bool]:
    """Add one quote to the counts; (in the primary set, word-changed)."""
    c["quotes"] += 1
    c["under_min_words"] += rec["n_words"] < audit.MIN_WORDS
    c["excluded_cue"] += rec["cue"]
    c["not_found"] += rec["category"] == vqc.NOT_FOUND
    if not audit.in_primary(rec):
        return False, False
    changed = explain.explain(quote, rec, eforms, essay_words)[0] == "word_changed"
    tight = rec["similarity"] >= TIGHT
    short = SHORT[0] <= rec["n_words"] <= SHORT[1]
    long_ = rec["n_words"] >= LONG_MIN
    c["n"] += 1
    c["prim_tight"] += tight
    c["n_short"] += short
    c["n_long"] += long_
    if changed:
        c["wc"] += 1
        c["wc_tight"] += tight
        c["wc_loose"] += not tight
        c["wc_short"] += short
        c["wc_long"] += long_
    return True, changed


def essay_rows(key: str, e: dict) -> list[dict]:
    """One row of counts per rank present for this essay."""
    essay = e["essay"]
    essay_words = vqc.words(essay)
    eforms = explain.essay_forms(essay)
    by_rank: dict = {}
    for text, (chosen, rejected) in e["feedback"].items():
        c = by_rank.setdefault(rank(chosen, rejected), dict.fromkeys(KEYS, 0))
        c["feedback"] += 1
        primary = changed = 0
        for quote, context in audit.extract_quotes(text):
            rec = audit.classify(essay, essay_words, "", quote, context)
            p, w = tally(c, quote, rec, eforms, essay_words)
            primary += p
            changed += w
        c["feedback_quoting"] += primary > 0
        c["feedback_with_wc"] += changed > 0
    return [{"essay": key, "set": e["set"], "rank": r, "counts": c} for r, c in sorted(by_rank.items())]


def total(rows: list[dict], pred) -> dict:
    t = dict.fromkeys(KEYS, 0)
    for r in rows:
        if pred(r):
            for k in KEYS:
                t[k] += r["counts"][k]
    return t


def per_essay(rows: list[dict], pred, num: str, den: str) -> list[tuple[int, int]]:
    """(numerator, denominator) per essay, summed over the selected rows."""
    d: dict = {}
    for r in rows:
        if pred(r):
            a = d.setdefault(r["essay"], [0, 0])
            a[0] += r["counts"][num]
            a[1] += r["counts"][den]
    return [tuple(v) for _, v in sorted(d.items())]


def paired(rows: list[dict], side_a: tuple, side_b: tuple) -> list[tuple[int, int, int, int]]:
    """(num_a, den_a, num_b, den_b) per essay; each side = (pred, num key, den key)."""
    d: dict = {}
    for r in rows:
        for j, (pred, num, den) in enumerate((side_a, side_b)):
            if pred(r):
                q = d.setdefault(r["essay"], [0, 0, 0, 0])
                q[2 * j] += r["counts"][num]
                q[2 * j + 1] += r["counts"][den]
    return [tuple(v) for _, v in sorted(d.items())]


def summary(rows: list[dict], pred, rng: random.Random | None, reps: int) -> dict:
    out: dict = {"counts": total(rows, pred), "essays": len({r["essay"] for r in rows if pred(r)})}
    for name, (num, den) in RATES.items():
        pairs = per_essay(rows, pred, num, den)
        out[name] = audit.ratio(pairs)
        if rng is not None and name == "word_changed_rate":
            out[name + "_ci95"] = audit.boot_ratio(pairs, rng, reps)
    return out


def verdict_sign(ci, den_a: int, den_b: int, floor: int, labels: tuple[str, str]) -> str:
    """Verdict on the 95% CI of (rate a - rate b); the plan predicts a higher."""
    if ci is None or den_a < floor or den_b < floor:
        return "underpowered (fewer than %d quotes on a side)" % floor
    lo, hi = ci
    if lo > 0:
        return "held (%s higher)" % labels[0]
    if hi < 0:
        return "reversed (%s higher)" % labels[1]
    return "no clear difference"


def verdict_margin(ci, den_a: int, den_b: int, floor: int) -> str:
    """E3: top minus bottom is credibly above -MARGIN."""
    if ci is None or den_a < floor or den_b < floor:
        return "underpowered (fewer than %d quotes on a side)" % floor
    lo, hi = ci
    if lo > -MARGIN:
        return "held (top-ranked feedback is not more faithful by more than %.1f point)" % (100 * MARGIN)
    if hi < 0:
        return "did not hold (top-ranked feedback changes words less often)"
    return "inconclusive"


def diff_test(quads, labels: tuple[str, str], measure: str, rng: random.Random, reps: int) -> dict:
    a = audit.ratio([(q[0], q[1]) for q in quads])
    b = audit.ratio([(q[2], q[3]) for q in quads])
    ci = audit.boot_paired_diff(quads, rng, reps)
    den_a, den_b = sum(q[1] for q in quads), sum(q[3] for q in quads)
    return {"measure": measure, labels[0]: a, labels[1]: b,
            "diff": None if a is None or b is None else a - b, "diff_ci95": ci,
            "denominators": [den_a, den_b], "verdict": verdict_sign(ci, den_a, den_b, GROUP_FLOOR, labels)}


def analyse(rows: list[dict], reps: int = REPS, seed: str = SEED) -> dict:
    rng = random.Random(seed)
    res: dict = {"essays": len({r["essay"] for r in rows}), "rows": len(rows)}
    res["pooled"] = summary(rows, lambda r: True, rng, reps)
    res["by_rank"] = {k: summary(rows, lambda r, k=k: r["rank"] == k, rng, reps) for k in RANKS}
    res["by_set"] = {s: summary(rows, lambda r, s=s: r["set"] == s, None, reps)
                     for s in sorted({r["set"] for r in rows})}

    p = res["pooled"]
    tests: dict = {"E1_pooled_word_changed": {
        "measure": "word-changed rate among primary-set quotes, all distinct feedback texts",
        "high": WC_MAX, "value": p["word_changed_rate"], "ci95": p["word_changed_rate_ci95"],
        "denominator": p["counts"]["n"],
        "verdict": explain.verdict(p["word_changed_rate"], None, WC_MAX, p["counts"]["n"], FLOOR)}}
    quads = paired(rows, (lambda r: True, "wc_short", "n_short"), (lambda r: True, "wc_long", "n_long"))
    tests["E2_short_vs_long"] = diff_test(
        quads, ("short quotes", "long quotes"),
        "word-changed rate, 4-6-word quotes minus 11+-word quotes (paired by essay)", rng, reps)
    quads = paired(rows, (lambda r: r["rank"] == "top", "wc", "n"), (lambda r: r["rank"] == "bottom", "wc", "n"))
    t = diff_test(quads, ("top-ranked", "bottom-ranked"),
                  "word-changed rate, top-ranked minus bottom-ranked feedback (paired by essay)", rng, reps)
    t["margin"] = -MARGIN
    t["verdict"] = verdict_margin(t["diff_ci95"], t["denominators"][0], t["denominators"][1], GROUP_FLOOR)
    tests["E3_top_vs_bottom"] = t
    res["tests"] = tests
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, help="speceval_dataset.json, or a folder holding it")
    ap.add_argument("--name", default="speceval_dataset.json")
    ap.add_argument("--out", required=True, help="speceval.json path")
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--plan", default="PLAN-5.md")
    args = ap.parse_args(argv)

    path = args.data if os.path.isfile(args.data) else audit.find_file(args.data, args.name)
    if not path:
        print("dataset not found under %s" % args.data, file=sys.stderr)
        return 2
    with open(path, encoding="utf-8-sig") as fh:
        records = json.load(fh)
    essays, info = collect(records if isinstance(records, list) else [])
    del records
    print("%d records, %d essays" % (info["records"], len(essays)), file=sys.stderr)

    rows = [r for key in sorted(essays) for r in essay_rows(key, essays[key])]
    res = analyse(rows, args.reps)
    res.update(info)
    res["feedback_texts"] = sum(len(e["feedback"]) for e in essays.values())
    res["dataset_file"] = os.path.basename(path)
    res["dataset_sha256"] = audit.sha256_file(path)
    res["sha256_as_probed"] = res["dataset_sha256"] == SHA256
    res["audit_sha256"] = audit.sha256_file(audit.__file__)
    res["explain_sha256"] = audit.sha256_file(explain.__file__)
    res["checker_sha256"] = audit.sha256_file(vqc.__file__)
    if os.path.isfile(args.plan):
        res["plan_sha256"] = audit.sha256_file(args.plan)
    res["python"] = sys.version.split()[0]

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print(json.dumps({"essays": res["essays"], "feedback_texts": res["feedback_texts"],
                      "n": res["pooled"]["counts"]["n"], "sha256_as_probed": res["sha256_as_probed"],
                      "verdicts": {k: v["verdict"] for k, v in res["tests"].items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
