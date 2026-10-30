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
"""cues: what the rewrite-cue filter set aside in SpecEval (audit 5b)

Part of feedback-quote-audit, by MV2 of Munim, Inc. Made with AI agents working in his name.

Audit 5 kept 519 of SpecEval's 14,413 double-quoted passages; the rewrite-cue rule from audit 1 set
aside most of them. Its cue list mixes edit cues ("instead", "better") with citation cues ("for
example", "such as", "e.g.") that also introduce genuine quotes of the student. This pass, fixed in
PLAN-5b.md before it ran, splits matched 4+-word quotes into primary (no cue), cited (citation cues
only) and edit-cued sets, compares their word-changed rates, and replays audit 5's top-vs-bottom
comparison on primary + cited. The file is read in memory; only aggregate counts are written.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys

import audit
import explain
import speceval
import verbatim_quote_check as vqc

CITE_RE = re.compile(r"(?i)(?:\be\.g\.|\bfor example\b|\bsuch as\b|\bfor instance\b)")
GROUPS = ("primary", "cited", "edit", "wide")  # wide = primary + cited
PER = ("n", "wc", "wc_loose", "n_short", "wc_short", "n_long", "wc_long", "texts")
KEYS = ("feedback", "quotes", "matched4") + tuple("%s_%s" % (k, g) for g in GROUPS for k in PER)

REPS = 10_000
SEED = "feedback-quote-audit-5b-20261030"
GROUP_FLOOR = 100  # quotes needed in each side of a comparison (G2-G4)
BAND = 0.03  # G2 holds if cited minus primary is credibly within +-BAND


def group(rec: dict, context: str) -> str | None:
    """primary / cited / edit for a matched quote of at least MIN_WORDS words; None for the rest."""
    if rec["category"] not in audit.MATCHED or rec["n_words"] < audit.MIN_WORDS:
        return None
    if not rec["cue"]:
        return "primary"
    return "edit" if audit.CUE_RE.search(CITE_RE.sub(" ", context)) else "cited"


def essay_rows(key: str, e: dict) -> list[dict]:
    """One row of counts per rank present for this essay."""
    essay = e["essay"]
    essay_words = vqc.words(essay)
    eforms = explain.essay_forms(essay)
    by_rank: dict = {}
    for text, (chosen, rejected) in e["feedback"].items():
        c = by_rank.setdefault(speceval.rank(chosen, rejected), dict.fromkeys(KEYS, 0))
        c["feedback"] += 1
        seen = set()
        for quote, context in audit.extract_quotes(text):
            c["quotes"] += 1
            rec = audit.classify(essay, essay_words, "", quote, context)
            g = group(rec, context)
            if g is None:
                continue
            c["matched4"] += 1
            changed = explain.explain(quote, rec, eforms, essay_words)[0] == "word_changed"
            short = speceval.SHORT[0] <= rec["n_words"] <= speceval.SHORT[1]
            long_ = rec["n_words"] >= speceval.LONG_MIN
            names = (g,) if g == "edit" else (g, "wide")
            for name in names:
                seen.add(name)
                c["n_" + name] += 1
                c["n_short_" + name] += short
                c["n_long_" + name] += long_
                if changed:
                    c["wc_" + name] += 1
                    c["wc_loose_" + name] += rec["similarity"] < speceval.TIGHT
                    c["wc_short_" + name] += short
                    c["wc_long_" + name] += long_
        for name in seen:
            c["texts_" + name] += 1
    return [{"essay": key, "set": e["set"], "rank": r, "counts": c} for r, c in sorted(by_rank.items())]


def total(rows: list[dict], pred) -> dict:
    t = dict.fromkeys(KEYS, 0)
    for r in rows:
        if pred(r):
            for k in KEYS:
                t[k] += r["counts"][k]
    return t


def summary(rows: list[dict], pred, rng: random.Random | None, reps: int) -> dict:
    out: dict = {"counts": total(rows, pred), "essays": len({r["essay"] for r in rows if pred(r)})}
    for g in GROUPS:
        rates: dict = {}
        for name, num, den in (("word_changed_rate", "wc", "n"), ("short_rate", "wc_short", "n_short"),
                               ("long_rate", "wc_long", "n_long"), ("loose_share_of_changed", "wc_loose", "wc")):
            pairs = speceval.per_essay(rows, pred, num + "_" + g, den + "_" + g)
            rates[name] = audit.ratio(pairs)
            if rng is not None and name == "word_changed_rate":
                rates[name + "_ci95"] = audit.boot_ratio(pairs, rng, reps)
        out[g] = rates
    return out


def verdict_band(ci, den_a: int, den_b: int, floor: int, band: float = BAND) -> str:
    """G2: the 95% CI of (a - b) lies within +-band."""
    if ci is None or den_a < floor or den_b < floor:
        return "underpowered (fewer than %d quotes on a side)" % floor
    lo, hi = ci
    if lo > -band and hi < band:
        return "held (within %.1f points)" % (100 * band)
    if lo > band or hi < -band:
        return "did not hold"
    return "inconclusive"


def diff(rows: list[dict], side_a: tuple, side_b: tuple, labels: tuple[str, str], measure: str,
         rng: random.Random, reps: int) -> dict:
    """(a - b) on the same essays, with the sign verdict of audit 5 (the plan predicts a higher)."""
    quads = speceval.paired(rows, side_a, side_b)
    a = audit.ratio([(q[0], q[1]) for q in quads])
    b = audit.ratio([(q[2], q[3]) for q in quads])
    ci = audit.boot_paired_diff(quads, rng, reps)
    den_a, den_b = sum(q[1] for q in quads), sum(q[3] for q in quads)
    return {"measure": measure, labels[0]: a, labels[1]: b,
            "diff": None if a is None or b is None else a - b, "diff_ci95": ci, "denominators": [den_a, den_b],
            "verdict": speceval.verdict_sign(ci, den_a, den_b, GROUP_FLOOR, labels)}


def analyse(rows: list[dict], reps: int = REPS, seed: str = SEED) -> dict:
    rng = random.Random(seed)
    res: dict = {"essays": len({r["essay"] for r in rows}), "rows": len(rows)}
    res["pooled"] = summary(rows, lambda r: True, rng, reps)
    res["by_rank"] = {k: summary(rows, lambda r, k=k: r["rank"] == k, rng, reps) for k in speceval.RANKS}

    c = res["pooled"]["counts"]
    tests: dict = {"G1_cited_vs_primary_count": {
        "measure": "matched 4+-word quotes: cited set size vs primary set size",
        "cited": c["n_cited"], "primary": c["n_primary"],
        "verdict": "held" if c["n_cited"] >= c["n_primary"] else "did not hold"}}
    every = lambda r: True  # noqa: E731
    t = diff(rows, (every, "wc_cited", "n_cited"), (every, "wc_primary", "n_primary"), ("cited", "primary"),
             "word-changed rate, cited minus primary quotes (paired by essay)", rng, reps)
    t["band"] = BAND
    t["verdict"] = verdict_band(t["diff_ci95"], t["denominators"][0], t["denominators"][1], GROUP_FLOOR)
    tests["G2_cited_vs_primary_rate"] = t
    tests["G3_edit_vs_cited"] = diff(
        rows, (every, "wc_edit", "n_edit"), (every, "wc_cited", "n_cited"), ("edit-cued", "cited"),
        "word-changed rate, edit-cued minus cited quotes (paired by essay)", rng, reps)
    tests["G4_bottom_vs_top_wide"] = diff(
        rows, (lambda r: r["rank"] == "bottom", "wc_wide", "n_wide"),
        (lambda r: r["rank"] == "top", "wc_wide", "n_wide"), ("bottom-ranked", "top-ranked"),
        "word-changed rate on primary + cited quotes, bottom-ranked minus top-ranked feedback (paired by essay)",
        rng, reps)
    res["tests"] = tests
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, help="speceval_dataset.json, or a folder holding it")
    ap.add_argument("--name", default="speceval_dataset.json")
    ap.add_argument("--out", required=True, help="cues.json path")
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--plan", default="PLAN-5b.md")
    args = ap.parse_args(argv)

    path = args.data if os.path.isfile(args.data) else audit.find_file(args.data, args.name)
    if not path:
        print("dataset not found under %s" % args.data, file=sys.stderr)
        return 2
    with open(path, encoding="utf-8-sig") as fh:
        records = json.load(fh)
    essays, info = speceval.collect(records if isinstance(records, list) else [])
    del records
    print("%d records, %d essays" % (info["records"], len(essays)), file=sys.stderr)

    rows = [r for key in sorted(essays) for r in essay_rows(key, essays[key])]
    res = analyse(rows, args.reps)
    res.update(info)
    res["feedback_texts"] = sum(len(e["feedback"]) for e in essays.values())
    res["dataset_file"] = os.path.basename(path)
    res["dataset_sha256"] = audit.sha256_file(path)
    res["sha256_as_probed"] = res["dataset_sha256"] == speceval.SHA256
    for name, mod in (("audit", audit), ("explain", explain), ("checker", vqc), ("speceval", speceval)):
        res[name + "_sha256"] = audit.sha256_file(mod.__file__)
    if os.path.isfile(args.plan):
        res["plan_sha256"] = audit.sha256_file(args.plan)
    res["python"] = sys.version.split()[0]

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    c = res["pooled"]["counts"]
    print(json.dumps({"essays": res["essays"], "feedback_texts": res["feedback_texts"],
                      "n": {g: c["n_" + g] for g in GROUPS}, "sha256_as_probed": res["sha256_as_probed"],
                      "verdicts": {k: v["verdict"] for k, v in res["tests"].items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
