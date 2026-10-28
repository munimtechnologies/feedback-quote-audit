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
"""band: why do stronger essays get more changed quotes in GLM-4.7's feedback? (audit 2b)

Part of feedback-quote-audit, by MV2 of Munim, Inc. Made with AI agents working in his name.

Audit 2 found a surprise: in GLM-4.7's published IELTS feedback, essays at band 7.0 or above get
their words changed in quotes more often than essays at band 5.5 or below, even with quote length
held fixed. Audit 2 read no quotes, so RESULTS-2.md listed three untested explanations. This pass,
fixed in PLAN-2b.md before it ran, tests them on the same data, filters and classes (it imports
audit.py and explain.py), using only aggregate counts:

- T1 (cue exclusion). Does the model mark its corrections with a rewrite cue (which takes the quote
  out of the primary set) more often for weak essays? If so the low band's primary set is cleaner.
- T2 (similarity robustness). Keep only quotes whose best match in the essay is tight (word-level
  similarity >= 0.8, i.e. a genuine quote attempt). Does the high band still change words more often?
- T3 (loose matches). Among the changed quotes, are the high band's a looser match of the essay
  (similarity below 0.8) more often -- the signature of a suggested phrase quoted as if from the
  essay, rather than a real misquote?

Only aggregate counts are written; no essay or feedback text is.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from multiprocessing import Pool

import audit
import explain
import verbatim_quote_check as vqc

TIGHT = 0.8  # word-level similarity at which a best match counts as a genuine quote attempt
REPS = 10_000
SEED = "feedback-quote-audit-2b-20261028"
GROUP_FLOOR = 100
# Per-essay counts; "eligible" is matched and at least MIN_WORDS words, before cue/question exclusion.
KEYS = ("eligible", "cue_excl", "n", "prim_tight", "wc", "wc_tight", "wc_loose")
# Audit 1/2 primary-set totals (results.json / length.json, 2026-10-26/27); this pass must reproduce them.
EARLIER = {"n": 50742, "low_quotes": 20520, "high_quotes": 2712}

# (id, numerator key, denominator key, predicted sign of low-minus-high, what it means)
TESTS = (
    ("T1_cue_exclusion", "cue_excl", "eligible", +1,
     "rewrite-cue exclusion rate (predicted higher for weak essays)"),
    ("T2_changed_rate_tight", "wc_tight", "prim_tight", -1,
     "word-changed rate among tight (similarity >= 0.8) matches (predicted still higher for strong essays)"),
    ("T3_loose_share_of_changed", "wc_loose", "wc", -1,
     "share of changed quotes that are a loose (similarity < 0.8) match (predicted higher for strong essays)"),
)
PREDICTED = tuple(t[0] for t in TESTS)


def buckets(rec: dict, cls: str | None) -> dict:
    """Count increments for one extracted quote. Pure: no text, no difflib, no I/O.

    `rec` is audit.classify's record; `cls` is explain.explain's class for primary quotes (else None).
    """
    b = dict.fromkeys(KEYS, 0)
    if rec["category"] not in audit.MATCHED or rec["n_words"] < audit.MIN_WORDS:
        return b
    b["eligible"] = 1
    if rec["cue"]:
        b["cue_excl"] = 1
    if rec["cue"] or rec["question"]:  # excluded from the primary set
        return b
    b["n"] = 1
    tight = rec["similarity"] >= TIGHT
    if tight:
        b["prim_tight"] = 1
    if cls == "word_changed":
        b["wc"] = 1
        if tight:
            b["wc_tight"] = 1
        else:
            b["wc_loose"] = 1
    return b


def band_row(row: dict) -> dict:
    """Per-essay counts of its feedback quotes, by audit 1's filters and 1b's classes."""
    question, essay, _ = audit.split_source(row["human"])
    essay_words = vqc.words(essay)
    eforms = explain.essay_forms(essay)
    c = dict.fromkeys(KEYS, 0)
    for quote, context in audit.extract_quotes(row["evaluation"]):
        rec = audit.classify(essay, essay_words, question, quote, context)
        cls = explain.explain(quote, rec, eforms, essay_words)[0] if audit.in_primary(rec) else None
        for k, v in buckets(rec, cls).items():
            c[k] += v
    return {"idx": row["idx"], "band": audit.parse_band(row["band"]), **c}


def verdict_dir(ci, n_low: int, n_high: int, floor: int, sign: int) -> str:
    """Verdict on the 95% CI of (low rate - high rate), given the predicted sign of the difference."""
    if ci is None or n_low < floor or n_high < floor:
        return "underpowered (fewer than %d quotes in a group)" % floor
    lo, hi = ci
    if sign > 0:  # predicted low band higher
        if lo > 0:
            return "held (weak essays higher)"
        if hi < 0:
            return "reversed (strong essays higher)"
    else:  # predicted high band higher
        if hi < 0:
            return "held (strong essays higher)"
        if lo > 0:
            return "reversed (weak essays higher)"
    return "no clear difference"


def _group_test(low, high, num, den, rng, reps):
    lp = [(r[num], r[den]) for r in low]
    hp = [(r[num], r[den]) for r in high]
    n_low = sum(d for _, d in lp)
    n_high = sum(d for _, d in hp)
    rl, rh = audit.ratio(lp), audit.ratio(hp)
    ci = audit.boot_group_diff(lp, hp, rng, reps)
    diff = None if rl is None or rh is None else rl - rh
    return {"low_rate": rl, "high_rate": rh, "low_denom": n_low, "high_denom": n_high,
            "diff_low_minus_high": diff, "diff_ci95": ci}


def analyse(rows: list[dict], reps: int = REPS, seed: str = SEED) -> dict:
    rng = random.Random(seed)
    low = [r for r in rows if r["band"] is not None and r["band"] <= audit.LOW_BAND_MAX]
    high = [r for r in rows if r["band"] is not None and r["band"] >= audit.HIGH_BAND_MIN]
    tot = {k: sum(r[k] for r in rows) for k in KEYS}
    res: dict = {"rows": len(rows), "low_essays": len(low), "high_essays": len(high), "totals": tot}
    tests: dict = {}
    for tid, num, den, sign, label in TESTS:
        t = _group_test(low, high, num, den, rng, reps)
        t["measure"] = label
        t["predicted_sign"] = sign
        t["verdict"] = verdict_dir(t["diff_ci95"], t["low_denom"], t["high_denom"], GROUP_FLOOR, sign)
        tests[tid] = t
    # Reference, no prediction: the raw (not length-standardised) word-changed rate by band, which
    # audit 2 reported standardised as B2. T2 and T3 explain its two parts.
    r0 = _group_test(low, high, "wc", "n", rng, reps)
    r0["measure"] = "raw word-changed rate by band (reference; audit 2 B2 is the length-standardised test)"
    r0["verdict"] = "descriptive"
    tests["R0_changed_rate_all"] = r0
    res["tests"] = tests
    res["consistent_with_earlier"] = (
        tot["n"] == EARLIER["n"]
        and sum(r["n"] for r in low) == EARLIER["low_quotes"]
        and sum(r["n"] for r in high) == EARLIER["high_quotes"])
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, help="dataset file, or a folder to search for --name")
    ap.add_argument("--name", default="glm47_final.jsonl")
    ap.add_argument("--out", required=True, help="band.json path")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="first N rows only (testing)")
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--plan", default="PLAN-2b.md")
    args = ap.parse_args(argv)

    path = args.data if os.path.isfile(args.data) else audit.find_file(args.data, args.name)
    if not path:
        print("dataset file not found under %s" % args.data, file=sys.stderr)
        return 2
    rows, read = [], 0
    for idx, rec in enumerate(audit.iter_records(path)):
        if args.limit and idx >= args.limit:
            break
        read += 1
        row = audit.to_row(idx, rec)
        if row["human"].strip() and row["evaluation"].strip():
            rows.append(row)
    print("%d records read, %d usable" % (read, len(rows)), file=sys.stderr)

    if args.workers > 1:
        with Pool(args.workers) as pool:
            done = list(pool.imap(band_row, rows, chunksize=16))
    else:
        done = [band_row(r) for r in rows]
    del rows

    res = analyse(done, args.reps)
    res["records_read"] = read
    res["dataset_file"] = os.path.basename(path)
    res["dataset_sha256"] = audit.sha256_file(path)
    res["audit_sha256"] = audit.sha256_file(audit.__file__)
    res["explain_sha256"] = audit.sha256_file(explain.__file__)
    res["checker_sha256"] = audit.sha256_file(vqc.__file__)
    if os.path.isfile(args.plan):
        res["plan_sha256"] = audit.sha256_file(args.plan)
    res["python"] = sys.version.split()[0]

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print(json.dumps({"rows": res["rows"], "n": res["totals"]["n"],
                      "consistent_with_earlier": res["consistent_with_earlier"],
                      "verdicts": {k: v["verdict"] for k, v in res["tests"].items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
