#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Audit 8b (PLAN-8b.md): what are the code snippets in ProgFeed hints that are not in the student's file?

Audit 8 found that 37 of 177 backtick code spans in gpt-4o-mini's natural-language hints (ProgFeed,
github.com/umass-ml4ed/progFeed-dataset-public at commit e020c7c0, CC BY 4.0) are in neither the student's
submitted file nor the problem text or prompt. This script re-uses audit8.py's span extraction and
classification unchanged and asks two things of each such snippet:

1. How close is it to code the student wrote? Best token-level similarity (difflib ratio) against any window
   of the student's file that is one token shorter, the same length or one token longer.
2. Does it turn up in the student's final submission of the lab (when that is later than the hinted one),
   compared with how often it turns up in other students' final submissions of the same lab?

Only counts are written: no code, no hint text and no student ids. Standard library only.
Usage: python audit8b.py run --tar progfeed.tar.gz --out audit8b-progfeed.json --md audit8b-progfeed.md
"""
import argparse
import difflib
import json
import os
import re
import statistics
import sys
import time

import audit8

AUDIT8_SHA256_LF = "3a95bc68e2c2f4e52d1b958c6e2a8a0568f9b1cc093b9ce0c7ec1ce7342b75b9"
SEED = 20261102
REPS = 10000
NEAR = 0.8
PARTIAL = 0.5
BANDS = ("near", "partial", "new")
FLOOR_Q1 = 30
FLOOR_Q2 = 20

TOKEN_RE = re.compile(r"\w+|[^\w\s]")
DIGITS_RE = re.compile(r"\d+")


def tokens(s):
    return TOKEN_RE.findall(s or "")


def best_similarity(span, text):
    """Highest difflib ratio between the span's tokens and any window of len-1, len or len+1 tokens of text."""
    s = tokens(span)
    f = tokens(text)
    if not s or not f:
        return 0.0
    sm = difflib.SequenceMatcher(None, autojunk=False)
    sm.set_seq2(s)
    k = len(s)
    best = 0.0
    for size in sorted(set(max(1, min(len(f), n)) for n in (k - 1, k, k + 1))):
        for i in range(len(f) - size + 1):
            sm.set_seq1(f[i:i + size])
            if sm.real_quick_ratio() <= best or sm.quick_ratio() <= best:
                continue
            r = sm.ratio()
            if r > best:
                best = r
                if best >= 1.0:
                    return 1.0
    return best


def band(sim):
    if sim >= NEAR:
        return "near"
    if sim >= PARTIAL:
        return "partial"
    return "new"


def ts_key(ts):
    """Order submission timestamps by the numbers in them, then by the raw string."""
    return tuple(int(x) for x in DIGITS_RE.findall(ts or "")), ts or ""


def submissions(by_folder):
    """{(lab, student): [ts, ...] in time order} from audit8.folders() keys all_labs/<lab>/<student>/<ts>/."""
    subs = {}
    for folder in by_folder:
        p = folder.split("/")
        if len(p) < 4:
            continue
        subs.setdefault((p[1], p[2]), []).append(p[3])
    for key in subs:
        subs[key].sort(key=ts_key)
    return subs


def contains(pair, s):
    text, text_nows = pair
    return s in text or audit8.nows(s) in text_nows


def analyse(units, files, by_folder, ctx):
    """One record per code span in the hints: status (audit 8's), similarity band, final-submission checks."""
    subs = submissions(by_folder)
    lab_students = {}
    for lab, student in subs:
        lab_students.setdefault(lab, []).append(student)
    cache = {}

    def text_of(lab, student, ts, source_file):
        key = (lab, student, ts, source_file)
        if key not in cache:
            how, t = audit8.source_for({"lab": lab, "student": student, "ts": ts, "source_file": source_file,
                                        "snippet": ""}, files, by_folder)
            cache[key] = None if how == "snippet" else (t, audit8.nows(t))
        return cache[key]

    recs = []
    for u in units:
        _how, text = audit8.source_for(u, files, by_folder)
        context = ctx.get(audit8.lab_key(u["lab"]), "") + "\n" + (u["function"] or "")
        text_nows, ctx_nows = audit8.nows(text), audit8.nows(context)
        now = ts_key(u["ts"])
        later = [t for t in subs.get((u["lab"], u["student"]), []) if ts_key(t) > now]
        final = text_of(u["lab"], u["student"], later[-1], u["source_file"]) if later else None
        for where, s in audit8.extract_spans(u["text"]):
            if audit8.span_kind(where, s) != "code":
                continue
            status = audit8.code_status(s, text, text_nows, context, ctx_nows)
            r = {"student": u["student"], "lab": u["lab"], "status": status, "tokens": len(tokens(s)),
                 "in_final": None, "control": None, "sim": None, "band": None}
            if final is not None:
                r["in_final"] = contains(final, s)
            if status in ("unsourced", "context"):
                r["sim"] = best_similarity(s, text)
                r["band"] = band(r["sim"])
            if status == "unsourced" and final is not None:
                hits = n = 0
                for other in lab_students.get(u["lab"], []):
                    if other == u["student"]:
                        continue
                    ot = text_of(u["lab"], other, subs[(u["lab"], other)][-1], u["source_file"])
                    if ot is None:
                        continue
                    n += 1
                    hits += 1 if contains(ot, s) else 0
                r["control"] = hits / n if n else None
            recs.append(r)
    return recs


def diff_verdict(ci, den, floor):
    if den < floor or ci is None:
        return "underpowered"
    lo, hi = ci
    if lo > 0:
        return "held"
    if hi < 0:
        return "reversed"
    return "no clear difference"


def judge(recs, reps=REPS):
    uns = [r for r in recs if r["status"] == "unsourced"]
    g1 = audit8.by_student([(r["student"], 1 if r["band"] == "near" else 0, 1) for r in uns])
    num1 = sum(g[0] for g in g1)
    den1 = sum(g[1] for g in g1)
    ci1 = audit8.cluster_ci(g1, reps, SEED) if den1 >= FLOOR_Q1 else None
    q1 = {"id": "Q1", "what": "unsourced code spans that are near-copies of the student's code (similarity >= 0.8)",
          "direction": ">", "threshold": 50.0, "floor": FLOOR_Q1, "unit": "unsourced code spans",
          "num": num1, "den": den1, "students": len(g1),
          "rate_pct": round(100.0 * num1 / den1, 2) if den1 else None,
          "ci95": None if ci1 is None else [round(ci1[0], 2), round(ci1[1], 2)],
          "verdict": audit8.verdict(ci1, den1, FLOOR_Q1, 50.0, ">")}
    both = [r for r in uns if r["in_final"] is not None and r["control"] is not None]
    g2 = audit8.by_student([(r["student"], (1.0 if r["in_final"] else 0.0) - r["control"], 1) for r in both])
    den2 = sum(g[1] for g in g2)
    ci2 = audit8.cluster_ci(g2, reps, SEED) if den2 >= FLOOR_Q2 else None
    q2 = {"id": "Q2", "what": "unsourced code spans appear in the recipient's later final submission more often "
                             "than in other students' final submissions of the same lab (difference > 0)",
          "floor": FLOOR_Q2, "unit": "unsourced code spans with a later final submission", "den": den2,
          "students": len(g2),
          "recipient_in_final": sum(1 for r in both if r["in_final"]),
          "control_mean_pct": round(100.0 * sum(r["control"] for r in both) / den2, 2) if den2 else None,
          "mean_diff_pts": round(100.0 * sum(g[0] for g in g2) / den2, 2) if den2 else None,
          "ci95": None if ci2 is None else [round(ci2[0], 2), round(ci2[1], 2)],
          "verdict": diff_verdict(ci2, den2, FLOOR_Q2)}
    return [q1, q2]


def summarise(recs):
    out = {}
    for status in audit8.CODE_KEYS:
        rs = [r for r in recs if r["status"] == status]
        later = [r for r in rs if r["in_final"] is not None]
        d = {"spans": len(rs), "students": len(set(r["student"] for r in rs)),
             "median_tokens": statistics.median([r["tokens"] for r in rs]) if rs else None,
             "with_later_final": len(later), "in_final": sum(1 for r in later if r["in_final"])}
        if status in ("unsourced", "context"):
            d["bands"] = {b: sum(1 for r in rs if r["band"] == b) for b in BANDS}
        if status == "unsourced":
            c = [r for r in later if r["control"] is not None]
            d["with_control"] = len(c)
            d["control_mean_pct"] = round(100.0 * sum(r["control"] for r in c) / len(c), 2) if c else None
            d["in_final_by_band"] = {b: [sum(1 for r in later if r["band"] == b and r["in_final"]),
                                         sum(1 for r in later if r["band"] == b)] for b in BANDS}
        out[status] = d
    return out


def per_lab(recs):
    out = {}
    for lab in sorted(set(r["lab"] for r in recs)):
        rs = [r for r in recs if r["lab"] == lab]
        uns = [r for r in rs if r["status"] == "unsourced"]
        out[lab] = {"code_spans": len(rs), "unsourced": len(uns),
                    "bands": {b: sum(1 for r in uns if r["band"] == b) for b in BANDS}}
    return out


def write_md(report, path):
    q1, q2 = report["predictions"]
    ci1 = "-" if not q1["ci95"] else "[%.1f, %.1f]" % tuple(q1["ci95"])
    ci2 = "-" if not q2["ci95"] else "[%.1f, %.1f]" % tuple(q2["ci95"])
    u = report["code_spans"]["unsourced"]
    lines = ["# Audit 8b: what are the hint code snippets that are not in the student's file?", "",
             "Counts only. Data: ProgFeed (umass-ml4ed/progFeed-dataset-public at %s, CC BY 4.0). "
             "Preregistered in PLAN-8b.md. Made with AI agents working in MV2's name." % audit8.PINNED_COMMIT[:8], "",
             "| id | prediction | n | observed | 95% CI | verdict |", "|---|---|---|---|---|---|",
             "| Q1 | %s > 50%% | %d | %s%% | %s | %s |" % (q1["what"], q1["den"], q1["rate_pct"], ci1, q1["verdict"]),
             "| Q2 | %s | %d | %s pts (recipient %d of %d, others %s%%) | %s | %s |" % (
                 q2["what"], q2["den"], q2["mean_diff_pts"], q2["recipient_in_final"], q2["den"],
                 q2["control_mean_pct"], ci2, q2["verdict"]), "",
             "unsourced: %s" % json.dumps(u, sort_keys=True), "",
             "context: %s" % json.dumps(report["code_spans"]["context"], sort_keys=True), "",
             "exact: %s" % json.dumps(report["code_spans"]["exact"], sort_keys=True), "",
             "ws: %s" % json.dumps(report["code_spans"]["ws"], sort_keys=True), "",
             "per lab: %s" % json.dumps(report["per_lab"], sort_keys=True)]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def run(args):
    t0 = time.time()
    tar_sha = audit8.sha256_file(args.tar)
    files = audit8.read_tar(args.tar)
    csv_bytes = files.pop("all_submissions_consolidated.csv", None)
    if csv_bytes is None:
        sys.exit("all_submissions_consolidated.csv is not in the archive")
    csv_text = audit8.dec(csv_bytes, "utf-8-sig")
    by_folder = audit8.folders(files)
    ctx = audit8.contexts(files)
    _rows, _typed, units = audit8.read_units(csv_text, "nl")
    recs = analyse(units, files, by_folder, ctx)
    here = os.path.dirname(os.path.abspath(__file__))
    report = {"audit": "8b", "plan": "PLAN-8b.md",
              "plan_sha256_lf": audit8.sha_lf_file(os.path.join(here, "PLAN-8b.md")),
              "audit8b_sha256_lf": audit8.sha_lf_file(os.path.abspath(__file__)),
              "audit8_sha256_lf": audit8.sha_lf_file(os.path.abspath(audit8.__file__)),
              "dataset": {"repo": "umass-ml4ed/progFeed-dataset-public", "commit": audit8.PINNED_COMMIT,
                          "license": "CC BY 4.0", "tar_sha256": tar_sha, "nl_units": len(units)},
              "near": NEAR, "partial": PARTIAL, "reps": args.reps, "seed": SEED,
              "code_spans": summarise(recs), "per_lab": per_lab(recs),
              "predictions": judge(recs, args.reps)}
    report["seconds"] = round(time.time() - t0, 1)
    report["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    if args.md:
        write_md(report, args.md)
    for p in report["predictions"]:
        print(p["id"], p["verdict"], p.get("rate_pct", p.get("mean_diff_pts")), p["ci95"], "n=%d" % p["den"])
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--tar", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--md", default="")
    r.add_argument("--reps", type=int, default=REPS)
    args = ap.parse_args(argv)
    if args.cmd == "run":
        got = audit8.sha_lf_file(os.path.abspath(audit8.__file__))
        if got != AUDIT8_SHA256_LF:
            sys.exit("audit8.py is not the file audit 8 ran (SHA-256 %s); not running" % got)
        run(args)


if __name__ == "__main__":
    main()
