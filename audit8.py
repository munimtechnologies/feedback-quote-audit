#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Audit 8 (PLAN-8.md): do classroom programming hints quote the student's code faithfully?

Data: ProgFeed (github.com/umass-ml4ed/progFeed-dataset-public at commit e020c7c0, CC BY 4.0), a
randomized classroom study in which gpt-4o-mini wrote natural-language hints ('nl') or failing test
cases ('tc') for failing Python submissions. The hint prompt held the problem description, the
student's whole submitted file and the prompt template. This script reads the consolidated table
all_submissions_consolidated.csv and each submission's source file under all_labs/, pulls every
backtick code span out of each hint, and asks whether it is in the student's file.

Only counts are written: no code, no feedback text and no student ids. Standard library only.
Usage: python audit8.py run --tar progfeed.tar.gz --out audit8-progfeed.json --md audit8-progfeed.md
"""
import argparse
import builtins
import csv
import hashlib
import io
import json
import keyword
import os
import random
import re
import sys
import tarfile
import time

PINNED_COMMIT = "e020c7c013187dba7b4130991eadc539d115526a"
SEED = 20261101
REPS = 10000

FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
INLINE_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
NAME_RE = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*(?:\(\))?")
NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
STRING_RE = re.compile(r"'[^'\n]*'|\"[^\"\n]*\"")
WS_RE = re.compile(r"\s+")

CODE_KEYS = ("exact", "ws", "context", "unsourced")
NAME_KEYS = ("file", "context", "known", "unsourced")
LIT_KEYS = ("file", "context", "other")

REQUIRED = ("student_id", "lab", "submission_timestamp", "ai_feedback_type", "ai_feedback_text",
            "source_file", "function_name", "code_snippet")

PREDICTIONS = [
    {"id": "P1", "what": "nl hints with at least one backtick code span", "direction": ">",
     "threshold": 50.0, "floor": 200, "unit": "hints"},
    {"id": "P2", "what": "code spans found in the student's submitted file (exact or whitespace-only difference)",
     "direction": ">", "threshold": 70.0, "floor": 150, "unit": "code spans"},
    {"id": "P3", "what": "found code spans that match the file exactly", "direction": ">",
     "threshold": 90.0, "floor": 150, "unit": "found code spans"},
    {"id": "P4", "what": "name spans found nowhere (not in the file, problem text or prompt, not a Python name)",
     "direction": "<", "threshold": 10.0, "floor": 150, "unit": "name spans"},
    {"id": "P5", "what": "hints with code spans that hold at least one code span found nowhere",
     "direction": "<", "threshold": 30.0, "floor": 100, "unit": "hints with code spans"},
]


def _known_names():
    known = set(keyword.kwlist) | set(dir(builtins)) | {"self", "cls"}
    for t in (str, list, dict, set, tuple, int, float, bytes, frozenset):
        known |= set(dir(t))
    return known


KNOWN = _known_names()


def dec(data, encoding="utf-8"):
    return data.decode(encoding, errors="replace")


def nows(s):
    return WS_RE.sub("", s)


def lab_key(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def extract_spans(text):
    """Return [(where, span)]: one stripped line of a fenced block ('block') or an inline span ('inline')."""
    text = text or ""
    spans = []
    for m in FENCE_RE.finditer(text):
        for line in m.group(1).splitlines():
            s = line.strip()
            if s:
                spans.append(("block", s))
    rest = FENCE_RE.sub(" ", text)
    for m in INLINE_RE.finditer(rest):
        s = m.group(1).strip()
        if s:
            spans.append(("inline", s))
    return spans


def span_kind(where, s):
    """'code', 'name' or 'literal'. Every line of a fenced block counts as code."""
    if where == "block":
        return "code"
    if s in ("True", "False", "None") or NUMBER_RE.fullmatch(s) or STRING_RE.fullmatch(s):
        return "literal"
    if NAME_RE.fullmatch(s):
        return "name"
    return "code"


def name_in(text, name):
    return re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text) is not None


def name_status(s, file_text, context):
    n = s[:-2] if s.endswith("()") else s
    if name_in(file_text, n):
        return "file"
    if name_in(context, n):
        return "context"
    if all(p in KNOWN or name_in(file_text, p) or name_in(context, p) for p in n.split(".")):
        return "known"
    return "unsourced"


def code_status(s, file_text, file_nows, context, context_nows):
    if s in file_text:
        return "exact"
    if nows(s) in file_nows:
        return "ws"
    if s in context or nows(s) in context_nows:
        return "context"
    return "unsourced"


def empty_rec():
    return {"spans": 0, "code": dict.fromkeys(CODE_KEYS, 0), "block": dict.fromkeys(CODE_KEYS, 0),
            "name": dict.fromkeys(NAME_KEYS, 0), "literal": dict.fromkeys(LIT_KEYS, 0), "fenced": False}


def audit_unit(text, file_text, context):
    file_nows = nows(file_text)
    ctx_nows = nows(context)
    rec = empty_rec()
    rec["fenced"] = bool(FENCE_RE.search(text or ""))
    for where, s in extract_spans(text):
        rec["spans"] += 1
        kind = span_kind(where, s)
        if kind == "code":
            st = code_status(s, file_text, file_nows, context, ctx_nows)
            rec["code"][st] += 1
            if where == "block":
                rec["block"][st] += 1
        elif kind == "name":
            rec["name"][name_status(s, file_text, context)] += 1
        else:
            st = "file" if s in file_text else ("context" if s in context else "other")
            rec["literal"][st] += 1
    return rec


def read_units(csv_text, feedback_type="nl"):
    """Return (rows, typed_rows, units). A unit is one delivered feedback text for one function of one submission."""
    try:
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        csv.field_size_limit(2 ** 31 - 1)
    reader = csv.DictReader(io.StringIO(csv_text, newline=""))
    missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError("CSV lacks columns: %s" % ", ".join(missing))
    rows = typed = 0
    units = {}
    for row in reader:
        rows += 1
        if (row.get("ai_feedback_type") or "").strip() != feedback_type:
            continue
        text = row.get("ai_feedback_text") or ""
        if not text.strip():
            continue
        typed += 1
        key = (row["student_id"], row["lab"], row["submission_timestamp"], row["source_file"],
               row["function_name"], text)
        if key not in units:
            units[key] = {"student": row["student_id"], "lab": row["lab"], "ts": row["submission_timestamp"],
                          "source_file": row["source_file"], "function": row["function_name"], "text": text,
                          "snippet": row.get("code_snippet") or ""}
    return rows, typed, list(units.values())


def read_tar(path):
    """Read the repository archive once; keep the CSV, submission files (not .json) and autograder .txt files."""
    files = {}
    with tarfile.open(path, "r|gz") as tf:
        for m in tf:
            if not m.isfile():
                continue
            parts = m.name.split("/", 1)
            if len(parts) != 2:
                continue
            rel = parts[1]
            keep = (rel == "all_submissions_consolidated.csv"
                    or (rel.startswith("all_labs/") and not rel.endswith(".json"))
                    or (rel.startswith("autograders/") and rel.endswith(".txt")))
            if keep:
                files[rel] = tf.extractfile(m).read()
    return files


def folders(files):
    out = {}
    for rel in files:
        if not rel.startswith("all_labs/"):
            continue
        p = rel.split("/")
        if len(p) >= 5:
            out.setdefault("/".join(p[:4]) + "/", []).append(rel)
    return out


def contexts(files):
    """Problem descriptions and prompt templates per lab, keyed by lab_key."""
    ctx = {}
    for rel, data in files.items():
        if not rel.startswith("autograders/"):
            continue
        p = rel.split("/")
        if len(p) < 3:
            continue
        name = p[-1]
        if not (name.endswith("_desc.txt") or name.startswith("openaiprompt")):
            continue
        key = lab_key(p[1].split("_autograder")[0])
        ctx.setdefault(key, []).append((rel, dec(data)))
    return {k: "\n".join(t for _, t in sorted(v)) for k, v in ctx.items()}


def source_for(unit, files, by_folder):
    """Return (how, text): the submitted file ('file'), all files of the submission ('folder') or the snippet."""
    folder = "all_labs/%s/%s/%s/" % (unit["lab"], unit["student"], unit["ts"])
    sf = (unit["source_file"] or "").replace("\\", "/")
    if sf and folder + sf in files:
        return "file", dec(files[folder + sf])
    names = by_folder.get(folder, [])
    base = sf.rsplit("/", 1)[-1]
    hits = [n for n in names if base and n.rsplit("/", 1)[-1] == base]
    if len(hits) == 1:
        return "file", dec(files[hits[0]])
    if names:
        return "folder", "\n".join(dec(files[n]) for n in sorted(names))
    return "snippet", unit["snippet"]


def metric_pairs(pid, recs):
    out = []
    for student, _lab, r in recs:
        code_n = sum(r["code"].values())
        if pid == "P1":
            out.append((student, 1 if r["spans"] else 0, 1))
        elif pid == "P2":
            out.append((student, r["code"]["exact"] + r["code"]["ws"], code_n))
        elif pid == "P3":
            out.append((student, r["code"]["exact"], r["code"]["exact"] + r["code"]["ws"]))
        elif pid == "P4":
            out.append((student, r["name"]["unsourced"], sum(r["name"].values())))
        elif pid == "P5":
            if code_n:
                out.append((student, 1 if r["code"]["unsourced"] else 0, 1))
        else:
            raise ValueError(pid)
    return out


def by_student(pairs):
    acc = {}
    for s, n, d in pairs:
        a = acc.setdefault(s, [0, 0])
        a[0] += n
        a[1] += d
    return [acc[s] for s in sorted(acc)]


def cluster_ci(groups, reps=REPS, seed=SEED):
    """Percentile 95% CI of the pooled rate (%), resampling students with replacement."""
    groups = [g for g in groups if g[1] > 0]
    if not groups:
        return None
    rng = random.Random(seed)
    k = len(groups)
    stats = []
    for _ in range(reps):
        n = d = 0
        for _ in range(k):
            g = groups[rng.randrange(k)]
            n += g[0]
            d += g[1]
        stats.append(100.0 * n / d)
    stats.sort()
    return stats[int(0.025 * reps)], stats[max(0, int(0.975 * reps) - 1)]


def verdict(ci, den, floor, threshold, direction):
    if den < floor or ci is None:
        return "underpowered"
    lo, hi = ci
    if direction == ">":
        if lo > threshold:
            return "holds"
        if hi < threshold:
            return "fails"
    else:
        if hi < threshold:
            return "holds"
        if lo > threshold:
            return "fails"
    return "inconclusive"


def judge(recs, reps=REPS):
    results = []
    for p in PREDICTIONS:
        groups = by_student(metric_pairs(p["id"], recs))
        num = sum(g[0] for g in groups)
        den = sum(g[1] for g in groups)
        rate = 100.0 * num / den if den else None
        ci = cluster_ci(groups, reps) if den >= p["floor"] else None
        r = dict(p)
        r.update({"num": num, "den": den, "students": sum(1 for g in groups if g[1] > 0),
                  "rate_pct": None if rate is None else round(rate, 2),
                  "ci95": None if ci is None else [round(ci[0], 2), round(ci[1], 2)],
                  "verdict": verdict(ci, den, p["floor"], p["threshold"], p["direction"])})
        results.append(r)
    return results


def totals(recs):
    t = {"hints": 0, "students": 0, "with_spans": 0, "spans": 0, "fenced": 0,
         "code": dict.fromkeys(CODE_KEYS, 0), "block": dict.fromkeys(CODE_KEYS, 0),
         "name": dict.fromkeys(NAME_KEYS, 0), "literal": dict.fromkeys(LIT_KEYS, 0)}
    students = set()
    for student, _lab, r in recs:
        students.add(student)
        t["hints"] += 1
        t["with_spans"] += 1 if r["spans"] else 0
        t["spans"] += r["spans"]
        t["fenced"] += 1 if r["fenced"] else 0
        for k in ("code", "block", "name", "literal"):
            for kk, v in r[k].items():
                t[k][kk] += v
    t["students"] = len(students)
    return t


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha_lf_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()
    except OSError:
        return None


def write_md(report, path):
    lines = ["# Audit 8: do classroom programming hints quote the student's code faithfully?", "",
             "Counts only. Data: ProgFeed (umass-ml4ed/progFeed-dataset-public at %s, CC BY 4.0). "
             "Preregistered in PLAN-8.md. Made with AI agents working in MV2's name." % PINNED_COMMIT[:8], "",
             "| id | prediction | n | rate % | 95% CI | verdict |", "|---|---|---|---|---|---|"]
    for p in report["predictions"]:
        ci = "-" if not p["ci95"] else "[%.1f, %.1f]" % (p["ci95"][0], p["ci95"][1])
        rate = "-" if p["rate_pct"] is None else "%.1f" % p["rate_pct"]
        lines.append("| %s | %s %s %.0f%% | %d | %s | %s | %s |" % (
            p["id"], p["what"], p["direction"], p["threshold"], p["den"], rate, ci, p["verdict"]))
    for name in ("nl", "tc"):
        t = report["totals"][name]
        lines += ["", "%s: %d hints from %d students, %d with spans, %d spans, %d with fenced blocks." % (
            name, t["hints"], t["students"], t["with_spans"], t["spans"], t["fenced"]),
            "code %s; block lines %s; names %s; literals %s; source match %s" % (
            json.dumps(t["code"]), json.dumps(t["block"]), json.dumps(t["name"]), json.dumps(t["literal"]),
            json.dumps(report["source_match"][name]))]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def run(args):
    t0 = time.time()
    tar_sha = sha256_file(args.tar)
    files = read_tar(args.tar)
    csv_bytes = files.pop("all_submissions_consolidated.csv", None)
    if csv_bytes is None:
        sys.exit("all_submissions_consolidated.csv is not in the archive")
    csv_text = dec(csv_bytes, "utf-8-sig")
    by_folder = folders(files)
    ctx = contexts(files)
    here = os.path.dirname(os.path.abspath(__file__))
    report = {"audit": 8, "plan": "PLAN-8.md",
              "plan_sha256_lf": sha_lf_file(os.path.join(here, "PLAN-8.md")),
              "audit8_sha256_lf": sha_lf_file(os.path.abspath(__file__)),
              "dataset": {"repo": "umass-ml4ed/progFeed-dataset-public", "commit": PINNED_COMMIT,
                          "license": "CC BY 4.0", "tar_sha256": tar_sha,
                          "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
                          "submission_files": sum(len(v) for v in by_folder.values()),
                          "labs_with_context": sorted(ctx)},
              "source_match": {}, "labs_without_context": {}, "totals": {}, "per_lab": {},
              "reps": args.reps, "seed": SEED}
    nl_recs = []
    for name in ("nl", "tc"):
        rows, typed, units = read_units(csv_text, name)
        report["dataset"]["csv_rows"] = rows
        report["dataset"]["%s_rows" % name] = typed
        report["dataset"]["%s_units" % name] = len(units)
        recs = []
        how_counts = {"file": 0, "folder": 0, "snippet": 0}
        no_ctx = 0
        for u in units:
            how, text = source_for(u, files, by_folder)
            how_counts[how] += 1
            c = ctx.get(lab_key(u["lab"]))
            if c is None:
                no_ctx += 1
                c = ""
            recs.append((u["student"], u["lab"], audit_unit(u["text"], text, c + "\n" + (u["function"] or ""))))
        report["source_match"][name] = how_counts
        report["labs_without_context"][name] = no_ctx
        report["totals"][name] = totals(recs)
        if name == "nl":
            nl_recs = recs
            labs = sorted(set(lab for _, lab, _ in recs))
            report["per_lab"] = {lab: totals([r for r in recs if r[1] == lab]) for lab in labs}
    report["predictions"] = judge(nl_recs, args.reps)
    report["seconds"] = round(time.time() - t0, 1)
    report["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    if args.md:
        write_md(report, args.md)
    for p in report["predictions"]:
        print(p["id"], p["verdict"], p["rate_pct"], p["ci95"], "n=%d" % p["den"])
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
        run(args)


if __name__ == "__main__":
    main()
