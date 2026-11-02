#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Audit 9 (PLAN-9.md): when a math tutor restates the student's work, is it what the student said?

Data: MRBench v3 as released for the BEA 2025 shared task (github.com/kaushal0494/UnifyingAITutorEvaluation
at commit 12c258f3, folder BEA_Shared_Task_2025_Datasets, CC BY-SA 4.0). Each item is a math tutoring
dialogue cut where the student makes a mistake, plus the next tutor turn written by several LLMs and by human
tutors. The dev set names the tutors and carries human labels; the test set's tutors are anonymous.

Units (fixed in PLAN-9.md before any outcome was computed):
- restatement sentence: a sentence of a tutor reply with a restatement cue ("you said", "you got",
  "you calculated", "your answer", "how did you get", ...; not after "if", "can", "did", ...) and at least one
  number once step/line references and ordinals are removed. Class: "student" (a number in the sentence is in
  a student turn), "equivalent" (equal in value to a student number, fraction or percent), "context" (only in
  the tutor turns of the dialogue, which hold the problem) or "nowhere".
- quoted span (descriptive only): a double-quoted span of 2+ words in a reply, set aside as a "wrapper" when it
  is 60% or more of the reply's words; else "student" / "context" (exact word run) / "near" (similarity at
  least 0.8 to a student turn) / "nowhere".

Only counts are written: no dialogue text, reply text or ids. Standard library only.
Usage: python audit9.py run --data mrbench_v3_devset.json mrbench_v3_testset.json --out audit9-mrbench.json
       [--md audit9-mrbench.md]
"""
import argparse
import difflib
import hashlib
import json
import os
import random
import re
import sys
import time

PINNED_COMMIT = "12c258f397d6df5892c773349499f5c36b7f567c"
DATA_SHA256 = {
    "mrbench_v3_devset.json": "a395feab801de50d44b73e1e9b88f84824a1f1d92e15ae86842d90c2b6dbf33c",
    "mrbench_v3_testset.json": "5a73434fd9e1dfc73026e146d3709f95f2483a51a5e5b354bc96d981448d92cd",
}
SEED = 20261103
REPS = 10000
FLOOR_LEVEL = 150
FLOOR_SIDE = 30
R1_THRESHOLD = 5.0
R2_THRESHOLD = 2.0
NEAR = 0.8
WRAPPER = 0.6
HUMAN = ("Expert", "Novice")
LLM = ("GPT4", "Gemini", "Llama318B", "Llama31405B", "Mistral", "Phi3", "Sonnet")
CLASSES = ("student", "equivalent", "context", "nowhere")
QCLASSES = ("student", "context", "near", "nowhere")
ML_LABELS = ("Yes", "To some extent", "No")

LQ, RQ = chr(0x201C), chr(0x201D)
QUOTE_RE = re.compile(r'"([^"\n]{1,300})"|' + LQ + r"([^" + RQ + r"\n]{1,300})" + RQ)
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
WORD_RE = re.compile(r"\w+")
SENT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
TURN_RE = re.compile(r"\s*(tutor|student)\s*:\s?(.*)", re.I)
THOUSANDS_RE = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
STRIP_RE = re.compile(r"\b(?:step|line|part|question|problem|row|equation)\s+\d+\b|\b\d+(?:st|nd|rd|th)\b", re.I)
FRAC_RE = re.compile(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)")
PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
YOU_RE = re.compile(r"\byour?\b", re.I)

SIMPLE = ("said", "say", "wrote", "got", "found", "calculated", "computed", "mentioned", "answered", "stated",
          "came up with", "arrived at", "counted", "added", "multiplied", "subtracted", "divided", "used")
PERFECT = ("said", "written", "gotten", "found", "calculated", "computed", "mentioned", "answered", "stated",
           "come up with", "arrived at", "counted", "added", "multiplied", "subtracted", "divided", "used")


def _alt(words):
    return "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in words)


STRICT_RE = re.compile(r"\byou\s+(?:" + _alt(SIMPLE) + r")\b|\byou(?:'ve|\s+have)\s+(?:" + _alt(PERFECT)
                       + r")\b|\byour\s+answer\b", re.I)
HOWDID_RE = re.compile(r"\b(?:how|where|why)\s+did\s+you\s+(?:get|come\s+up\s+with|arrive\s+at|find|calculate|"
                       r"compute|work\s+out)\b", re.I)
BROAD_RE = re.compile(r"\byou(?:'ve|\s+have|\s+had|\s+get)\b|\byour\s+(?:calculation|result|solution|total|work|"
                      r"final)\b", re.I)
HYPO = frozenset(("if", "when", "once", "whether", "unless", "until", "can", "could", "would", "should", "will",
                  "might", "may", "must", "shall", "did", "do", "does", "have", "has", "had"))
NUMBER_WORDS = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
                "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12",
                "thirteen": "13", "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
                "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
                "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90", "hundred": "100",
                "thousand": "1000", "dozen": "12"}


def norm(text):
    return (text or "").replace(chr(0x2019), "'")


def turns(history):
    """[(speaker, text)] from a 'Tutor: ... / Student: ...' history; unlabelled lines join the previous turn."""
    out = []
    for line in (history or "").split("\n"):
        m = TURN_RE.match(line)
        if m:
            out.append([m.group(1).capitalize(), m.group(2)])
        elif out:
            out[-1][1] += "\n" + line
    return [(s, t) for s, t in out]


def canon(s):
    """'0.50' -> '0.5', '007' -> '7', '3.0' -> '3'."""
    if "." in s:
        ip, fp = s.split(".", 1)
        fp = fp.rstrip("0")
    else:
        ip, fp = s, ""
    ip = ip.lstrip("0") or "0"
    return ip + ("." + fp if fp else "")


def numbers(text, strip=False):
    t = THOUSANDS_RE.sub("", norm(text))
    if strip:
        t = STRIP_RE.sub(" ", t)
    return [canon(x) for x in NUM_RE.findall(t)]


def number_sets(texts):
    """Canonical digit strings and numeric values (incl. number words, fractions, percents) in the texts."""
    cset, vals = set(), set()
    for text in texts:
        t = THOUSANDS_RE.sub("", norm(text))
        for c in numbers(t):
            cset.add(c)
            vals.add(float(c))
        words = WORD_RE.findall(t.lower())
        for w in words:
            if w in NUMBER_WORDS:
                cset.add(NUMBER_WORDS[w])
                vals.add(float(NUMBER_WORDS[w]))
        if "half" in words:
            vals.add(0.5)
        for a, b in FRAC_RE.findall(t):
            if float(b) != 0:
                v = float(a) / float(b)
                vals.add(v)
                vals.add(v * 100)
        for p in PCT_RE.findall(t):
            vals.add(float(p) / 100)
    return cset, vals


def close(x, vals):
    return any(abs(x - v) <= 1e-9 * max(1.0, abs(v)) for v in vals)


def toks(text):
    return [w.lower() for w in WORD_RE.findall(norm(text))]


def has_run(hay, needle):
    k = len(needle)
    return k > 0 and any(hay[i:i + k] == needle for i in range(len(hay) - k + 1))


def best_sim(needle, hay):
    """Highest difflib ratio between needle tokens and any window of hay of len-1, len or len+1 tokens."""
    if not needle or not hay:
        return 0.0
    sm = difflib.SequenceMatcher(None, autojunk=False)
    sm.set_seq2(needle)
    k = len(needle)
    best = 0.0
    for size in sorted(set(max(1, min(len(hay), n)) for n in (k - 1, k, k + 1))):
        for i in range(len(hay) - size + 1):
            sm.set_seq1(hay[i:i + size])
            if sm.real_quick_ratio() <= best or sm.quick_ratio() <= best:
                continue
            r = sm.ratio()
            if r > best:
                best = r
    return best


def context(history):
    ts = turns(history)
    student = [t for s, t in ts if s == "Student"]
    tutor = [t for s, t in ts if s == "Tutor"]
    sc, sv = number_sets(student)
    tc, tv = number_sets(tutor)
    return {"s_canon": sc, "s_vals": sv, "t_canon": tc, "t_vals": tv,
            "s_toks": [toks(t) for t in student], "t_toks": [toks(t) for t in tutor]}


def cue_ok(sent, m):
    before = WORD_RE.findall(sent[:m.start()].lower())[-2:]
    return not any(w in HYPO for w in before)


def restatements(reply):
    """[(kind, numbers)] for sentences with a restatement cue and a number; kind 'strict' or 'broad'."""
    out = []
    for sent in SENT_RE.split(norm(reply)):
        if not sent or not NUM_RE.search(sent):
            continue
        if HOWDID_RE.search(sent) or any(cue_ok(sent, m) for m in STRICT_RE.finditer(sent)):
            kind = "strict"
        elif BROAD_RE.search(sent):
            kind = "broad"
        else:
            continue
        nums = numbers(sent, strip=True)
        if nums:
            out.append((kind, nums))
    return out


def classify(nums, ctx):
    if any(n in ctx["s_canon"] for n in nums):
        return "student"
    if any(close(float(n), ctx["s_vals"]) for n in nums):
        return "equivalent"
    if any(n in ctx["t_canon"] or close(float(n), ctx["t_vals"]) for n in nums):
        return "context"
    return "nowhere"


def quotes(reply):
    """[(span tokens, wrapper, attributed)] for double-quoted spans of 2+ words."""
    t = norm(reply)
    reply_words = len(WORD_RE.findall(t))
    out = []
    for m in QUOTE_RE.finditer(t):
        st = toks(m.group(1) or m.group(2))
        if len(st) < 2:
            continue
        wrapper = len(st) >= WRAPPER * reply_words
        attributed = bool(YOU_RE.search(t[max(0, m.start() - 80):m.start()]))
        out.append((st, wrapper, attributed))
    return out


def quote_class(st, ctx):
    if any(has_run(h, st) for h in ctx["s_toks"]):
        return "student"
    if any(has_run(h, st) for h in ctx["t_toks"]):
        return "context"
    if max([best_sim(st, h) for h in ctx["s_toks"]] or [0.0]) >= NEAR:
        return "near"
    return "nowhere"


def is_human(tutor):
    if tutor in HUMAN:
        return True
    if tutor in LLM:
        return False
    return None


def analyse(files):
    """files: [(file name, list of records)] -> (restatement units, quote units). Ids never leave this script."""
    units, qunits = [], []
    for fname, records in files:
        for i, rec in enumerate(records):
            if not isinstance(rec, dict):
                continue
            dlg = "%s:%s:%d" % (fname, rec.get("conversation_id", ""), i)
            ctx = context(rec.get("conversation_history", ""))
            for tutor, val in sorted((rec.get("tutor_responses") or {}).items()):
                if not isinstance(val, dict):
                    continue
                reply = val.get("response", "") or ""
                ann = val.get("annotation")
                ml = ann.get("Mistake_Location") if isinstance(ann, dict) else None
                base = {"dlg": dlg, "file": fname, "tutor": "%s/%s" % (fname, tutor), "human": is_human(tutor),
                        "ml": ml if ml in ML_LABELS else None}
                for kind, nums in restatements(reply):
                    u = dict(base)
                    u.update(kind=kind, cls=classify(nums, ctx))
                    units.append(u)
                for st, wrapper, attributed in quotes(reply):
                    q = dict(base)
                    q.update(wrapper=wrapper, attributed=attributed,
                             cls=None if wrapper else quote_class(st, ctx))
                    qunits.append(q)
    return units, qunits


def by_dialogue(rows):
    """rows: (dialogue, a, b, ...) -> per-dialogue sums, in a fixed order."""
    g = {}
    for row in rows:
        acc = g.setdefault(row[0], [0] * (len(row) - 1))
        for j, v in enumerate(row[1:]):
            acc[j] += v
    return [tuple(g[k]) for k in sorted(g)]


def _ci(groups, stat, reps, seed):
    if not groups:
        return None
    rng = random.Random(seed)
    n = len(groups)
    vals = []
    for _ in range(reps):
        v = stat([groups[rng.randrange(n)] for _ in range(n)])
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    vals.sort()
    return vals[int(0.025 * (len(vals) - 1))], vals[int(0.975 * (len(vals) - 1))]


def rate_stat(sample):
    den = sum(g[1] for g in sample)
    return 100.0 * sum(g[0] for g in sample) / den if den else None


def diff_stat(sample):
    da = sum(g[1] for g in sample)
    db = sum(g[3] for g in sample)
    if not da or not db:
        return None
    return 100.0 * sum(g[0] for g in sample) / da - 100.0 * sum(g[2] for g in sample) / db


def level_verdict(ci, den, floor, thr):
    if den < floor or ci is None:
        return "underpowered"
    if ci[0] > thr:
        return "held"
    if ci[1] < thr:
        return "did not hold"
    return "inconclusive"


def diff_verdict(ci, den_a, den_b, floor):
    if min(den_a, den_b) < floor or ci is None:
        return "underpowered"
    if ci[0] > 0:
        return "held"
    if ci[1] < 0:
        return "reversed"
    return "no clear difference"


def _r(x):
    return None if x is None else round(x, 2)


def _rci(ci):
    return None if ci is None else [round(ci[0], 2), round(ci[1], 2)]


def unsourced(u):
    return 1 if u["cls"] in ("context", "nowhere") else 0


def level(units, num_fn, reps, seed, floor, thr, pid, what):
    g = by_dialogue([(u["dlg"], num_fn(u), 1) for u in units])
    num, den = sum(x[0] for x in g), sum(x[1] for x in g)
    ci = _ci(g, rate_stat, reps, seed) if den >= floor else None
    return {"id": pid, "what": what, "direction": ">", "threshold": thr, "floor": floor,
            "num": num, "den": den, "dialogues": len(g), "rate_pct": _r(100.0 * num / den) if den else None,
            "ci95": _rci(ci), "verdict": level_verdict(ci, den, floor, thr)}


def compare(a_units, b_units, reps, seed, floor):
    rows = [(u["dlg"], unsourced(u), 1, 0, 0) for u in a_units] + \
           [(u["dlg"], 0, 0, unsourced(u), 1) for u in b_units]
    g = by_dialogue(rows)
    na, da = sum(x[0] for x in g), sum(x[1] for x in g)
    nb, db = sum(x[2] for x in g), sum(x[3] for x in g)
    ci = _ci(g, diff_stat, reps, seed) if min(da, db) >= floor else None
    return {"a_num": na, "a_den": da, "a_pct": _r(100.0 * na / da) if da else None,
            "b_num": nb, "b_den": db, "b_pct": _r(100.0 * nb / db) if db else None,
            "diff_pts": _r(100.0 * na / da - 100.0 * nb / db) if da and db else None,
            "dialogues": len(g), "ci95": _rci(ci), "verdict": diff_verdict(ci, da, db, floor)}


def judge(units, reps=REPS, floor_level=FLOOR_LEVEL, floor_side=FLOOR_SIDE):
    strict = [u for u in units if u["kind"] == "strict"]
    r1 = level(strict, unsourced, reps, SEED, floor_level, R1_THRESHOLD, "R1",
               "restatement sentences with no number from any student turn (context or nowhere), all tutors, "
               "dev + test")
    r2 = level(strict, lambda u: 1 if u["cls"] == "nowhere" else 0, reps, SEED + 1, floor_level, R2_THRESHOLD,
               "R2", "restatement sentences whose numbers are nowhere in the dialogue, all tutors, dev + test")
    a = [u for u in strict if u["ml"] in ("No", "To some extent")]
    b = [u for u in strict if u["ml"] == "Yes"]
    r3 = {"id": "R3", "what": "share with no student number is higher in replies labelled Mistake_Location "
                             "'No' or 'To some extent' (a) than in replies labelled 'Yes' (b), dev set",
          "floor": floor_side}
    r3.update(compare(a, b, reps, SEED + 2, floor_side))
    return [r1, r2, r3]


def tally(us, classes):
    d = {c: sum(1 for u in us if u["cls"] == c) for c in classes}
    d["n"] = len(us)
    return d


def describe(units, qunits, reps=REPS, floor_side=FLOOR_SIDE):
    strict = [u for u in units if u["kind"] == "strict"]
    broad = [u for u in units if u["kind"] == "broad"]
    out = {"strict": tally(strict, CLASSES), "broad": tally(broad, CLASSES)}
    for name, us in (("strict", strict), ("broad", broad)):
        out[name]["unsourced_pct"] = _r(100.0 * sum(unsourced(u) for u in us) / len(us)) if us else None
    per = {}
    for t in sorted(set(u["tutor"] for u in strict)):
        us = [u for u in strict if u["tutor"] == t]
        d = tally(us, CLASSES)
        d["unsourced_pct"] = _r(100.0 * sum(unsourced(u) for u in us) / len(us))
        per[t] = d
    out["per_tutor_strict"] = per
    llm = [u for u in strict if u["human"] is False]
    hum = [u for u in strict if u["human"] is True]
    out["llm_vs_human_dev"] = compare(llm, hum, reps, SEED + 3, floor_side)
    out["llm_vs_human_dev"].pop("verdict")
    out["llm_vs_human_dev"]["note"] = "descriptive, no verdict: a = LLM tutors, b = human tutors (dev set)"
    out["mistake_location_strict"] = {lab: tally([u for u in strict if u["ml"] == lab], CLASSES)
                                      for lab in ML_LABELS}
    q = {"spans": len(qunits), "wrappers": sum(1 for x in qunits if x["wrapper"])}
    rest = [x for x in qunits if not x["wrapper"]]
    q["attributed"] = tally([x for x in rest if x["attributed"]], QCLASSES)
    q["unattributed"] = tally([x for x in rest if not x["attributed"]], QCLASSES)
    q["per_tutor"] = {t: tally([x for x in rest if x["tutor"] == t], QCLASSES)
                      for t in sorted(set(x["tutor"] for x in rest))}
    q["wrappers_per_tutor"] = {t: sum(1 for x in qunits if x["wrapper"] and x["tutor"] == t)
                               for t in sorted(set(x["tutor"] for x in qunits if x["wrapper"]))}
    out["quotes"] = q
    return out


def sha_lf_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()
    except OSError:
        return None


def write_md(report, path):
    lines = ["# Audit 9: do math tutors restate the student's work correctly? (MRBench v3)", "",
             "Counts only. Data: MRBench v3 / BEA 2025 (kaushal0494/UnifyingAITutorEvaluation at %s, CC BY-SA 4.0). "
             "Preregistered in PLAN-9.md. Made with AI agents working in MV2's name." % PINNED_COMMIT[:8], "",
             "| id | prediction | n | observed | 95% CI | verdict |", "|---|---|---|---|---|---|"]
    for p in report["predictions"]:
        ci = "-" if not p["ci95"] else "[%.2f, %.2f]" % tuple(p["ci95"])
        if p["id"] == "R3":
            obs = "%s%% (%d/%d) vs %s%% (%d/%d), diff %s pts" % (p["a_pct"], p["a_num"], p["a_den"], p["b_pct"],
                                                                  p["b_num"], p["b_den"], p["diff_pts"])
            n = p["a_den"] + p["b_den"]
        else:
            obs = "%s%% (%d/%d); threshold %s%%" % (p["rate_pct"], p["num"], p["den"], p["threshold"])
            n = p["den"]
        lines.append("| %s | %s | %d | %s | %s | %s |" % (p["id"], p["what"], n, obs, ci, p["verdict"]))
    d = report["descriptive"]
    for key in ("strict", "broad", "llm_vs_human_dev", "mistake_location_strict", "per_tutor_strict", "quotes"):
        lines += ["", "%s: %s" % (key, json.dumps(d[key], sort_keys=True))]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def run(args):
    t0 = time.time()
    files, shas = [], {}
    for path in args.data:
        with open(path, "rb") as f:
            raw = f.read()
        name = os.path.basename(path)
        sha = hashlib.sha256(raw).hexdigest()
        if not args.allow_unpinned and DATA_SHA256.get(name) != sha:
            sys.exit("%s has SHA-256 %s, not the pinned file; not running" % (name, sha))
        data = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(data, list):
            sys.exit("%s: top-level JSON is not a list; not running" % name)
        shas[name] = {"sha256": sha, "bytes": len(raw), "records": len(data)}
        files.append((name, data))
    units, qunits = analyse(files)
    here = os.path.dirname(os.path.abspath(__file__))
    report = {"audit": "9", "plan": "PLAN-9.md",
              "plan_sha256_lf": sha_lf_file(os.path.join(here, "PLAN-9.md")),
              "audit9_sha256_lf": sha_lf_file(os.path.abspath(__file__)),
              "dataset": {"repo": "kaushal0494/UnifyingAITutorEvaluation", "commit": PINNED_COMMIT,
                          "license": "CC BY-SA 4.0", "files": shas, "pinned": not args.allow_unpinned},
              "seed": SEED, "reps": args.reps, "floors": {"level": FLOOR_LEVEL, "side": FLOOR_SIDE},
              "predictions": judge(units, args.reps),
              "descriptive": describe(units, qunits, args.reps)}
    report["seconds"] = round(time.time() - t0, 1)
    report["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    if args.md:
        write_md(report, args.md)
    for p in report["predictions"]:
        print(p["id"], p["verdict"], p.get("rate_pct", p.get("diff_pts")), p["ci95"], flush=True)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--data", nargs="+", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--md", default="")
    r.add_argument("--reps", type=int, default=REPS)
    r.add_argument("--allow-unpinned", action="store_true", help="tests only: skip the data SHA-256 check")
    args = ap.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    main()
