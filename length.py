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
"""length: do longer quotes change the student's words more often? (audit 2)

Part of feedback-quote-audit, by MV2 of Munim, Inc. Made with AI agents working in his name.

Follow-up 1b found that, once Markdown formatting and "..." are allowed for, 95.7% of the
quotes in GLM-4.7's IELTS feedback keep the student's words. This pass, fixed in PLAN-2.md
before it ran, takes the same primary-set quotes in the feedback (same data, filters and
classes: it imports audit.py and explain.py) and asks two things. Does the share of quotes
that change the student's words grow with quote length? And once 1b's classes are used and
quote length is held fixed, do weaker essays get more changed quotes than stronger ones?
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

# Quote length in words (the checker's word count), inclusive; None = no upper bound.
BINS = ((4, 6), (7, 10), (11, 15), (16, 25), (26, None))
BIN_NAMES = ("4-6", "7-10", "11-15", "16-25", "26+")
SHORT, LONG = 0, 4
# Bins merged for the band comparison, so each band has enough quotes in every stratum.
STRATA = ((0, 1), (2, 3), (4,))
STRATUM_NAMES = ("4-10", "11-25", "26+")
FORMATTING = ("emphasis", "typography", "spacing", "edges", "case")
KEYS = ("n", "words", "exact", "formatting", "changed", "unmarked", "edits")

REPS = 10_000
SEED = "feedback-quote-audit-2-20261027"
FLOOR = 300
GROUP_FLOOR = 100
# Totals from audit 1 (results.json) and 1b (explain.json), 2026-10-26/27; this pass must reproduce them.
EARLIER = {"n": 50742, "exact": 19148, "changed": 2193, "unmarked": 1434,
           "low_quotes": 20520, "high_quotes": 2712}

# (id, what is compared, numerator key, denominator key); every prediction is "difference above zero".
LENGTH_TESTS = (("L1", "changed", "n"), ("L2", "unmarked", "n"), ("L3", "edits", "words"))
BAND_TESTS = (("B1", "unmarked"), ("B2", "changed"), ("B3", "exact"), ("B4", "formatting"))
PREDICTED = ("L1", "L2", "L3", "B1", "B2")


def bin_of(n_words: int) -> int | None:
    for i, (lo, hi) in enumerate(BINS):
        if n_words >= lo and (hi is None or n_words <= hi):
            return i
    return None


def length_row(row: dict) -> dict:
    """Per-bin counts of one essay's primary-set feedback quotes, by 1b's classes."""
    question, essay, _ = audit.split_source(row["human"])
    essay_words = vqc.words(essay)
    eforms = explain.essay_forms(essay)
    c = {k: [0] * len(BINS) for k in KEYS}
    for quote, context in audit.extract_quotes(row["evaluation"]):
        rec = audit.classify(essay, essay_words, question, quote, context)
        if not audit.in_primary(rec):
            continue
        cls, _, emphasis = explain.explain(quote, rec, eforms, essay_words)
        b = bin_of(rec["n_words"])
        c["n"][b] += 1
        c["words"][b] += rec["n_words"]
        c["exact"][b] += cls == "exact"
        c["formatting"][b] += cls in FORMATTING
        if cls == "word_changed":
            c["changed"][b] += 1
            c["unmarked"][b] += not emphasis
            c["edits"][b] += rec["edits"]
    return {"idx": row["idx"], "band": audit.parse_band(row["band"]), **c}


def pairs(rows: list[dict], key: str, bins, den: str = "n") -> list[tuple[int, int]]:
    """(numerator, denominator) per essay, summed over the given bins."""
    return [(sum(r[key][b] for b in bins), sum(r[den][b] for b in bins)) for r in rows]


def by_length(rows: list[dict], rng: random.Random | None, reps: int) -> dict:
    out = {}
    for b, name in enumerate(BIN_NAMES):
        d: dict = {"quotes": sum(r["n"][b] for r in rows)}
        for key in ("exact", "formatting", "changed", "unmarked"):
            d[key + "_rate"] = audit.ratio(pairs(rows, key, (b,)))
        d["changed_words_per_word"] = audit.ratio(pairs(rows, "edits", (b,), "words"))
        if rng is not None:
            for key in ("changed", "unmarked"):
                d[key + "_rate_ci95"] = audit.boot_ratio(pairs(rows, key, (b,)), rng, reps)
        out[name] = d
    return out


def long_minus_short(rows: list[dict], key: str, den: str, rng: random.Random, reps: int) -> dict:
    """Rate in 26+-word quotes minus rate in 4-6-word quotes; CI paired by essay."""
    quads = [(r[key][LONG], r[den][LONG], r[key][SHORT], r[den][SHORT]) for r in rows]
    long_r = audit.ratio([(q[0], q[1]) for q in quads])
    short_r = audit.ratio([(q[2], q[3]) for q in quads])
    return {"long": long_r, "short": short_r,
            "diff": None if long_r is None or short_r is None else long_r - short_r,
            "diff_ci95": audit.boot_paired_diff(quads, rng, reps),
            "long_quotes": sum(r["n"][LONG] for r in rows), "short_quotes": sum(r["n"][SHORT] for r in rows)}


def strata_rows(rows: list[dict], key: str) -> list[tuple[int, ...]]:
    """Per essay: (num, quotes) for each stratum, flattened."""
    out = []
    for r in rows:
        t: list[int] = []
        for s in STRATA:
            t += [sum(r[key][b] for b in s), sum(r["n"][b] for b in s)]
        out.append(tuple(t))
    return out


def weights(rows: list[dict]) -> list[float]:
    """Share of all quotes in each stratum (fixed; not resampled)."""
    tot = [sum(r["n"][b] for r in rows for b in s) for s in STRATA]
    total = sum(tot)
    return [t / total if total else 0.0 for t in tot]


def std_rate(trows: list[tuple[int, ...]], w: list[float]) -> float | None:
    """Length-standardised rate: stratum rates weighted by w; None if a weighted stratum is empty."""
    rate = 0.0
    for i, wi in enumerate(w):
        if wi == 0:
            continue
        den = sum(t[2 * i + 1] for t in trows)
        if den == 0:
            return None
        rate += wi * sum(t[2 * i] for t in trows) / den
    return rate


def boot_std_diff(a, b, w, rng: random.Random, reps: int = REPS) -> tuple[float, float] | None:
    """95% CI of std_rate(a) - std_rate(b), two independent groups of essays."""
    if not a or not b:
        return None
    stats = []
    for _ in range(reps):
        x = std_rate(rng.choices(a, k=len(a)), w)
        y = std_rate(rng.choices(b, k=len(b)), w)
        if x is not None and y is not None:
            stats.append(x - y)
    if not stats:
        return None
    stats.sort()
    return audit._pct(stats, 0.025), audit._pct(stats, 0.975)


def band_compare(rows: list[dict], key: str, w: list[float], rng: random.Random, reps: int) -> dict:
    """Band <= 5.5 minus band >= 7.0 (audit 1's groups), raw and length-standardised."""
    low = [r for r in rows if r["band"] is not None and r["band"] <= audit.LOW_BAND_MAX]
    high = [r for r in rows if r["band"] is not None and r["band"] >= audit.HIGH_BAND_MIN]
    every = range(len(BINS))
    raw_l, raw_h = audit.ratio(pairs(low, key, every)), audit.ratio(pairs(high, key, every))
    la, ha = strata_rows(low, key), strata_rows(high, key)
    std_l, std_h = std_rate(la, w), std_rate(ha, w)
    low_by = [sum(t[2 * i + 1] for t in la) for i in range(len(STRATA))]
    high_by = [sum(t[2 * i + 1] for t in ha) for i in range(len(STRATA))]
    return {"low_essays": len(low), "high_essays": len(high),
            "low_quotes": sum(low_by), "high_quotes": sum(high_by),
            "low_quotes_by_stratum": dict(zip(STRATUM_NAMES, low_by)),
            "high_quotes_by_stratum": dict(zip(STRATUM_NAMES, high_by)),
            "low_raw": raw_l, "high_raw": raw_h,
            "raw_diff": None if raw_l is None or raw_h is None else raw_l - raw_h,
            "low_std": std_l, "high_std": std_h,
            "std_diff": None if std_l is None or std_h is None else std_l - std_h,
            "std_diff_ci95": boot_std_diff(la, ha, w, rng, reps),
            "smallest_stratum_quotes": min(low_by + high_by)}


def verdict_up(ci, smallest: int, floor: int) -> str:
    if ci is None or smallest < floor:
        return "underpowered (fewer than %d quotes in a group)" % floor
    lo, hi = ci
    if lo > 0:
        return "held (difference above zero)"
    if hi < 0:
        return "reversed (difference below zero)"
    return "no clear difference"


def analyse(rows: list[dict], reps: int = REPS, seed: str = SEED) -> dict:
    rng = random.Random(seed)
    every = range(len(BINS))
    tot = {k: sum(r[k][b] for r in rows for b in every) for k in KEYS}
    res: dict = {"rows": len(rows), "totals": tot, "by_length": by_length(rows, rng, reps)}
    tests: dict = {}
    for pid, key, den in LENGTH_TESTS:
        t = long_minus_short(rows, key, den, rng, reps)
        t["measure"] = key + " per " + ("quote" if den == "n" else "quoted word")
        t["verdict"] = verdict_up(t["diff_ci95"], min(t["long_quotes"], t["short_quotes"]), FLOOR)
        tests[pid] = t
    w = weights(rows)
    res["strata_weights"] = dict(zip(STRATUM_NAMES, w))
    for pid, key in BAND_TESTS:
        t = band_compare(rows, key, w, rng, reps)
        t["measure"] = key + " per quote"
        t["verdict"] = (verdict_up(t["std_diff_ci95"], t["smallest_stratum_quotes"], GROUP_FLOOR)
                        if pid in PREDICTED else "descriptive")
        tests[pid] = t
    res["tests"] = tests
    b3 = tests["B3"]
    res["consistent_with_earlier"] = all(
        (tot.get(k) if k in tot else b3[k]) == v for k, v in EARLIER.items())
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, help="dataset file, or a folder to search for --name")
    ap.add_argument("--name", default="glm47_final.jsonl")
    ap.add_argument("--out", required=True, help="length.json path")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="first N rows only (testing)")
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--plan", default="PLAN-2.md")
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
