#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Audit 9 groundwork probe: how often do tutor replies in MRBench v3 restate what the student said?

Data: the BEA 2025 shared-task files of MRBench v3 (github.com/kaushal0494/UnifyingAITutorEvaluation at commit
12c258f3, CC BY-SA 4.0; Maurya et al., NAACL 2025; Kochmar et al., BEA 2025). Each record is a math tutoring
dialogue cut where the student makes a mistake, plus the next tutor turn written by several LLMs and by human
tutors, with human labels (Mistake_Identification, Mistake_Location, Providing_Guidance, Actionability).

This probe counts OPPORTUNITIES only, so the audit-9 plan can set its floors before any outcome is computed:
dialogues, replies per tutor, double-quoted spans in replies and their length in words, replies with a number,
sentences that pair a second-person cue ("you said", "your answer", ...) with a number, and the label counts.
It never checks whether a quoted span or a number is found in the student's turns. Only counts are written:
no dialogue or reply text, no ids. Standard library only.

Usage: python probe9.py --data mrbench_v3_devset.json mrbench_v3_testset.json --out probe9.json
"""
import argparse
import hashlib
import json
import os
import re
import time

PINNED_COMMIT = "12c258f397d6df5892c773349499f5c36b7f567c"
DIMENSIONS = ("Mistake_Identification", "Mistake_Location", "Providing_Guidance", "Actionability")
LABELS = ("Yes", "To some extent", "No")
BANDS = ("0", "1", "2-3", "4-6", "7+")

LQ, RQ = chr(0x201C), chr(0x201D)
QUOTE_RE = re.compile(r'"([^"\n]{1,300})"|' + LQ + r"([^" + RQ + r"\n]{1,300})" + RQ)
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
WORD_RE = re.compile(r"\w+")
SENT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
TURN_RE = re.compile(r"\s*(tutor|student)\s*:\s?(.*)", re.I)
CUES = ("you said", "you say", "you wrote", "you got", "you get", "you found", "you calculated", "you computed",
        "you mentioned", "you answered", "you stated", "you came up with", "you arrived at", "you counted",
        "you added", "you multiplied", "you subtracted", "you divided", "you used", "you have", "you've",
        "you had", "your answer", "your calculation", "your result", "your solution", "your total", "your work",
        "your final")
CUE_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in CUES) + r")\b", re.I)


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


def quote_spans(text):
    return [a or b for a, b in QUOTE_RE.findall(text or "")]


def band(n):
    if n <= 0:
        return "0"
    if n == 1:
        return "1"
    if n <= 3:
        return "2-3"
    if n <= 6:
        return "4-6"
    return "7+"


def cue_number_hits(text):
    """One entry per cue found in a sentence that also holds a number."""
    hits = []
    for sent in SENT_RE.split(norm(text)):
        if not NUM_RE.search(sent):
            continue
        for m in CUE_RE.finditer(sent):
            hits.append(m.group(1).lower())
    return hits


def response_counts(text):
    return {"quotes": [len(WORD_RE.findall(s)) for s in quote_spans(text)],
            "has_number": bool(NUM_RE.search(text or "")),
            "cue_hits": cue_number_hits(text)}


def new_bucket():
    return {"responses": 0, "with_quote": 0, "quotes": 0, "quote_words": {b: 0 for b in BANDS},
            "with_number": 0, "with_cue_number": 0,
            "labels": {d: {lab: 0 for lab in LABELS + ("other",)} for d in DIMENSIONS}}


def add(bucket, c, ann):
    bucket["responses"] += 1
    if c["quotes"]:
        bucket["with_quote"] += 1
    bucket["quotes"] += len(c["quotes"])
    for n in c["quotes"]:
        bucket["quote_words"][band(n)] += 1
    if c["has_number"]:
        bucket["with_number"] += 1
    if c["cue_hits"]:
        bucket["with_cue_number"] += 1
    for d in DIMENSIONS:
        v = ann.get(d)
        bucket["labels"][d][v if v in LABELS else "other"] += 1


def probe(records):
    per, allc, cues = {}, new_bucket(), {}
    conversations = no_student = last_num = 0
    for rec in records:
        if not isinstance(rec, dict):
            continue
        conversations += 1
        st = [t for s, t in turns(rec.get("conversation_history", "")) if s == "Student"]
        if not st:
            no_student += 1
        elif NUM_RE.search(st[-1]):
            last_num += 1
        for tutor, val in sorted((rec.get("tutor_responses") or {}).items()):
            if not isinstance(val, dict):
                continue
            c = response_counts(val.get("response", ""))
            ann = val.get("annotation") or {}
            for b in (per.setdefault(tutor, new_bucket()), allc):
                add(b, c, ann)
            for h in c["cue_hits"]:
                cues[h] = cues.get(h, 0) + 1
    return {"conversations": conversations, "no_student_turn": no_student,
            "student_last_turn_with_number": last_num, "responses": allc["responses"],
            "all": allc, "per_tutor": per, "cue_number_sentences": dict(sorted(cues.items()))}


def run(args):
    t0 = time.time()
    report = {"probe": "audit-9 groundwork (opportunity counts only)", "dataset_commit": PINNED_COMMIT,
              "license": "CC BY-SA 4.0", "files": {}}
    for path in args.data:
        raw = open(path, "rb").read()
        name = os.path.basename(path)
        data = json.loads(raw.decode("utf-8-sig"))
        if isinstance(data, list):
            res = probe(data)
        else:
            res = {"error": "top-level JSON is %s, not a list" % type(data).__name__}
        res["sha256"] = hashlib.sha256(raw).hexdigest()
        res["bytes"] = len(raw)
        report["files"][name] = res
        print(name, res.get("conversations"), "dialogues", res.get("responses"), "replies", flush=True)
    report["seconds"] = round(time.time() - t0, 1)
    report["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    main()
