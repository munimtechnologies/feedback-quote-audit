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
"""length_tight: are changed quotes genuine misquotes or near-misses, by quote length? (audit 3)

Part of feedback-quote-audit, by MV2 of Munim, Inc. Made with AI agents working in his name.

Audit 2b split the word-changed quotes in GLM-4.7's IELTS feedback into two kinds by the checker's
best-match similarity. A "tight" change (similarity >= 0.8) is a close copy of an essay span with a
word altered -- a genuine misquote. A "loose" change (similarity below 0.8) matches no close span --
the signature of a suggested phrase quoted as if it were the student's. Across all the feedback,
53.2% of the 2,193 changed quotes are loose. This pass, fixed in PLAN-3.md before it ran, asks how
that tight/loose split varies with quote length. That tells quote-check how much of its "changed
words" signal at each length is likely near-miss noise rather than a real misquote. Same data,
filters and classes as audits 1, 1b, 2 and 2b (it imports audit.py and explain.py). Only aggregate
counts are written; no essay or feedback text is.
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

TIGHT = 0.8  # word-level best-match similarity at or above which a match counts as tight
# Quote length in words (the checker's word count), inclusive; None = no upper bound.
BINS = ((4, 6), (7, 10), (11, 15), (16, 25), (26, None))
BIN_NAMES = ("4-6", "7-10", "11-15", "16-25", "26+")
# Short and long strata for the predicted length comparison; the 7-10 bin is a gap (table only).
SHORT_BINS = (0,)        # 4-6 words
LONG_BINS = (2, 3, 4)    # 11+ words
SHORT_NAME, LONG_NAME = "4-6", "11+"
KEYS = ("n", "prim_tight", "wc", "wc_tight", "wc_loose")

REPS = 10_000
SEED = "feedback-quote-audit-3-20261028"
FLOOR = 100  # quotes needed in each stratum's denominator for a verdict
# Totals from audit 2b (band.json, 2026-10-28); this pass must reproduce them.
EARLIER = {"n": 50742, "prim_tight": 48677, "wc": 2193, "wc_tight": 1026, "wc_loose": 1167}

# (id, numerator key, denominator key, predicted sign of long-minus-short, what it means)
TESTS = (
    ("A1_tight_changed_rate", "wc_tight", "prim_tight", +1,
     "word-changed rate among tight (similarity >= 0.8) matches (predicted higher for long quotes)"),
    ("A2_loose_share_of_changed", "wc_loose", "wc", -1,
     "share of changed quotes that are a loose (similarity < 0.8) match (predicted higher for short quotes)"),
)
PREDICTED = tuple(t[0] for t in TESTS)


def bin_of(n_words: int) -> int | None:
    for i, (lo, hi) in enumerate(BINS):
        if n_words >= lo and (hi is None or n_words <= hi):
            return i
    return None


def counts(similarity: float, cls: str) -> dict:
    """Per-quote increments for one primary-set quote. Pure: no text, no difflib, no I/O.

    `similarity` is audit.classify's rec['similarity']; `cls` is explain.explain's class.
    """
    c = dict.fromkeys(KEYS, 0)
    c["n"] = 1
    tight = similarity >= TIGHT
    if tight:
        c["prim_tight"] = 1
    if cls == "word_changed":
        c["wc"] = 1
        if tight:
            c["wc_tight"] = 1
        else:
            c["wc_loose"] = 1
    return c


def length_row(row: dict) -> dict:
    """Per-bin counts of one essay's primary-set feedback quotes, by 2b's tight/loose split."""
    question, essay, _ = audit.split_source(row["human"])
    essay_words = vqc.words(essay)
    eforms = explain.essay_forms(essay)
    c = {k: [0] * len(BINS) for k in KEYS}
    for quote, context in audit.extract_quotes(row["evaluation"]):
        rec = audit.classify(essay, essay_words, question, quote, context)
        if not audit.in_primary(rec):
            continue
        b = bin_of(rec["n_words"])
        if b is None:
            continue
        cls = explain.explain(quote, rec, eforms, essay_words)[0]
        for k, v in counts(rec["similarity"], cls).items():
            c[k][b] += v
    return {"idx": row["idx"], **c}


def pairs(rows: list[dict], key: str, bins, den: str = "n") -> list[tuple[int, int]]:
    """(numerator, denominator) per essay, summed over the given bins."""
    return [(sum(r[key][b] for b in bins), sum(r[den][b] for b in bins)) for r in rows]


def by_length(rows: list[dict], rng: random.Random | None, reps: int) -> dict:
    out = {}
    for b, name in enumerate(BIN_NAMES):
        d: dict = {"quotes": sum(r["n"][b] for r in rows),
                   "tight_matches": sum(r["prim_tight"][b] for r in rows),
                   "changed": sum(r["wc"][b] for r in rows)}
        d["changed_rate"] = audit.ratio(pairs(rows, "wc", (b,)))
        d["tight_changed_rate"] = audit.ratio(pairs(rows, "wc_tight", (b,), "prim_tight"))
        d["loose_share_of_changed"] = audit.ratio(pairs(rows, "wc_loose", (b,), "wc"))
        if rng is not None:
            d["tight_changed_rate_ci95"] = audit.boot_ratio(pairs(rows, "wc_tight", (b,), "prim_tight"), rng, reps)
            d["loose_share_of_changed_ci95"] = audit.boot_ratio(pairs(rows, "wc_loose", (b,), "wc"), rng, reps)
        out[name] = d
    return out


def long_minus_short(rows: list[dict], num: str, den: str, rng: random.Random, reps: int) -> dict:
    """Rate in LONG (11+) quotes minus rate in SHORT (4-6) quotes; CI paired by essay."""
    quads = [(sum(r[num][b] for b in LONG_BINS), sum(r[den][b] for b in LONG_BINS),
              sum(r[num][b] for b in SHORT_BINS), sum(r[den][b] for b in SHORT_BINS)) for r in rows]
    long_r = audit.ratio([(q[0], q[1]) for q in quads])
    short_r = audit.ratio([(q[2], q[3]) for q in quads])
    return {"long": long_r, "short": short_r,
            "diff_long_minus_short": None if long_r is None or short_r is None else long_r - short_r,
            "diff_ci95": audit.boot_paired_diff(quads, rng, reps),
            "long_denom": sum(q[1] for q in quads), "short_denom": sum(q[3] for q in quads)}


def verdict_dir(ci, long_denom: int, short_denom: int, floor: int, sign: int) -> str:
    """Verdict on the 95% CI of (long rate - short rate), given the predicted sign of the difference."""
    if ci is None or long_denom < floor or short_denom < floor:
        return "underpowered (fewer than %d quotes in a stratum)" % floor
    lo, hi = ci
    if sign > 0:  # predicted long band higher
        if lo > 0:
            return "held (long quotes higher)"
        if hi < 0:
            return "reversed (short quotes higher)"
    else:  # predicted short band higher
        if hi < 0:
            return "held (short quotes higher)"
        if lo > 0:
            return "reversed (long quotes higher)"
    return "no clear difference"


def analyse(rows: list[dict], reps: int = REPS, seed: str = SEED) -> dict:
    rng = random.Random(seed)
    every = range(len(BINS))
    tot = {k: sum(r[k][b] for r in rows for b in every) for k in KEYS}
    res: dict = {"rows": len(rows), "totals": tot, "strata": {"short": SHORT_NAME, "long": LONG_NAME},
                 "by_length": by_length(rows, rng, reps)}
    tests: dict = {}
    for tid, num, den, sign, label in TESTS:
        t = long_minus_short(rows, num, den, rng, reps)
        t["measure"] = label
        t["predicted_sign"] = sign
        t["verdict"] = verdict_dir(t["diff_ci95"], t["long_denom"], t["short_denom"], FLOOR, sign)
        tests[tid] = t
    # Reference, no prediction: the overall loose share of changed, reproducing audit 2b.
    overall = audit.ratio(pairs(rows, "wc_loose", tuple(every), "wc"))
    tests["R0_loose_share_all"] = {
        "measure": "overall share of changed quotes that are a loose match (reference; audit 2b = 0.532)",
        "value": overall, "denominator": tot["wc"], "verdict": "descriptive"}
    res["tests"] = tests
    res["consistent_with_earlier"] = all(tot[k] == v for k, v in EARLIER.items())
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, help="dataset file, or a folder to search for --name")
    ap.add_argument("--name", default="glm47_final.jsonl")
    ap.add_argument("--out", required=True, help="length-tight.json path")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="first N rows only (testing)")
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--plan", default="PLAN-3.md")
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
            done = list(pool.imap(length_row, rows, chunksize=16))
    else:
        done = [length_row(r) for r in rows]
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
