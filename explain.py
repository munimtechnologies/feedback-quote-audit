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
"""explain: why are most published feedback quotes not character-exact? (audit 1b)

Part of feedback-quote-audit, by MV2 of Munim, Inc. Made with AI agents working in his name.

Audit 1 found that 37.7% of the primary-set quotes in GLM-4.7's IELTS feedback are exact copies
of the essay while 92.3% keep the student's words. This pass, fixed in PLAN-1b.md before it ran,
takes the same quotes (same data, filters and code: it imports audit.py) and records for each the
first formatting step after which it is found in the essay: Markdown emphasis removed, curly
quotes and dashes made plain, spacing around punctuation made uniform, punctuation and ellipses
at the quote's ends dropped, capitals ignored, and finally an ellipsis inside the quote read as
"words left out". Quotes that still do not match have changed the student's words; for those it
counts which carry Markdown emphasis (a marked correction) and what kind of change the rest make.
Only aggregate counts are written; no essay or feedback text. The optional review sample is not
published.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import random
import re
import sys
from multiprocessing import Pool

import audit
import verbatim_quote_check as vqc

STEPS = ("exact", "emphasis", "typography", "spacing", "edges", "case", "elision")
CLASSES = STEPS + ("other_punctuation", "elision_words", "word_changed")
KINDS = ("negation", "spelling_or_form", "word_swap", "added_or_dropped")
COUNT_KEYS = (("n",) + CLASSES + ("altered", "altered_elision", "wc_emphasis", "wc_unmarked",
                                  "wc_elided", "wc_unmarked_plain") + tuple("unmarked_" + k for k in KINDS))

EMPHASIS_RE = re.compile(r"\*+|__+")
TYPOGRAPHY = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "`": "'", "´": "'",
                            "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',
                            "…": "...", "–": "-", "—": "-"})
# '...', '. . .', '[...]' or the single ellipsis character, with any spaces around it.
ELLIPSIS_RE = re.compile(r"\s*(?:\[\s*(?:\.\s*){3,}\]|(?:\.\s*){3,}|…)\s*")
EDGE = " .,;:!?'\"()[]-"
NEGATIONS = frozenset({"not", "no", "never", "nor", "cannot", "t", "neither", "none", "nobody", "nothing"})
SPELLING_RATIO = 0.6  # character similarity at which a one-for-one word change counts as spelling/form

REPS = 10_000
SEED = "feedback-quote-audit-1b-20261026"
FLOOR = 300
GROUP_FLOOR = 100
# Audit 1's primary-set totals (results.json, 2026-10-26); this pass must reproduce them.
AUDIT1 = {"evaluation": {"primary_matched": 50742, "exact": 19148},
          "reasoning": {"primary_matched": 109676, "exact": 71024}}

# name: (numerator count keys, denominator count key)
MEASURES = {
    "char_match_after_case": (STEPS[:6], "n"),
    "char_match_after_elision": (STEPS, "n"),
    "word_faithful_with_elision": (CLASSES[:-1], "n"),
    "word_changed_rate": (("word_changed",), "n"),
    "unmarked_word_changed_rate": (("wc_unmarked",), "n"),
    "elision_share_of_altered": (("altered_elision",), "altered"),
    "emphasis_share_of_word_changed": (("wc_emphasis",), "word_changed"),
}
# (id, measure, lowest value that holds or None, highest value that holds or None)
PREDICTIONS = (
    ("P1", "char_match_after_case", 0.80, None),
    ("P2", "elision_share_of_altered", 0.30, 0.70),
    ("P3", "word_changed_rate", None, 0.05),
    ("P4", "emphasis_share_of_word_changed", 0.20, None),
    ("P5", "unmarked_word_changed_rate", 0.01, 0.04),
)


def _spacing(x: str) -> str:
    """One space between words, none before , . ; : ! ? ) ] or after ( [, one after , ; : ! ?"""
    x = re.sub(r"\s+", " ", x)
    x = re.sub(r" (?=[,.;:!?)\]])", "", x)
    x = re.sub(r"(?<=[(\[]) ", "", x)
    x = re.sub(r"([,;:!?])(?=[^\s\d,;:!?.)\]'\"])", r"\1 ", x)
    return x.strip()


def _forms(text: str) -> list[str]:
    """The text after steps 1-3, cumulatively: [raw, emphasis, typography, spacing]."""
    t1 = EMPHASIS_RE.sub("", text)
    t2 = t1.translate(TYPOGRAPHY)
    return [text, t1, t2, _spacing(t2)]


def essay_forms(essay: str) -> list[str]:
    """The essay as compared at steps 0-5 (the edges step changes only the quote)."""
    f = _forms(essay)
    return f + [f[3], f[3].casefold()]


def quote_forms(quote: str) -> list[str]:
    """The quote as compared at steps 0-5."""
    f = _forms(vqc.clean_quote(quote))
    edges = f[3].strip(EDGE)
    return f + [edges, edges.casefold()]


def fragments(text: str) -> list[str]:
    """Pieces of a quote between ellipses, ends stripped, empty pieces dropped."""
    return [p for p in (s.strip(EDGE) for s in ELLIPSIS_RE.split(text)) if p]


def in_order(pieces: list[str], text: str) -> bool:
    """Every piece is found in text, in order and not overlapping."""
    if not pieces:
        return False
    pos = 0
    for p in pieces:
        i = text.find(p, pos)
        if i < 0:
            return False
        pos = i + len(p)
    return True


def words_in_order(pieces: list[list[str]], src_words: list[str]) -> bool:
    """Every piece is a contiguous run of src_words, the runs in order and not overlapping."""
    if not pieces:
        return False
    pos = 0
    for p in pieces:
        m = len(p)
        for i in range(pos, len(src_words) - m + 1):
            if src_words[i:i + m] == p:
                pos = i + m
                break
        else:
            return False
    return True


def first_step(quote: str, eforms: list[str]) -> int | None:
    """Index into STEPS of the first step after which the quote is found in the essay, else None."""
    qf = quote_forms(quote)
    for k in range(6):
        if qf[k] and qf[k] in eforms[k]:
            return k
    pieces = fragments(qf[5])
    if len(pieces) > 1 and in_order(pieces, eforms[5]):
        return 6
    return None


def explain(quote: str, rec: dict, eforms: list[str], essay_words: list[str]) -> tuple[str, bool, bool]:
    """(class, elided, emphasis) for one primary-set quote; rec is audit.classify's record."""
    plain = vqc.clean_quote(quote).translate(TYPOGRAPHY)
    pieces = [w for w in (vqc.words(p) for p in ELLIPSIS_RE.split(plain)) if w]
    elided = len(pieces) > 1
    emphasis = bool(EMPHASIS_RE.search(quote))
    k = first_step(quote, eforms)
    if k is not None:
        return STEPS[k], elided, emphasis
    if rec["category"] in (vqc.EXACT, vqc.PUNCT_WHITESPACE):
        return "other_punctuation", elided, emphasis
    if elided and words_in_order(pieces, essay_words):
        return "elision_words", elided, emphasis
    return "word_changed", elided, emphasis


def change_kinds(rec: dict) -> dict:
    """What differs between a changed-words quote and audit 1's closest essay passage."""
    q = vqc.words(rec["quote"])
    w = rec["passage"].split()
    kinds = dict.fromkeys(KINDS, False)
    kinds["negation"] = sum(t in NEGATIONS for t in q) != sum(t in NEGATIONS for t in w)
    sm = difflib.SequenceMatcher(None, w, q, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace" and i2 - i1 == j2 - j1:
            for a, b in zip(w[i1:i2], q[j1:j2]):
                if difflib.SequenceMatcher(None, a, b).ratio() >= SPELLING_RATIO:
                    kinds["spelling_or_form"] = True
                else:
                    kinds["word_swap"] = True
        elif tag == "replace":
            kinds["word_swap"] = True
        elif tag in ("insert", "delete"):
            kinds["added_or_dropped"] = True
    return kinds


def explain_row(row: dict) -> dict:
    question, essay, _ = audit.split_source(row["human"])
    essay_words = vqc.words(essay)
    eforms = essay_forms(essay)
    out = {"idx": row["idx"], "review": []}
    for field in audit.FIELDS:
        counts = dict.fromkeys(COUNT_KEYS, 0)
        for quote, context in audit.extract_quotes(row[field]):
            rec = audit.classify(essay, essay_words, question, quote, context)
            if not audit.in_primary(rec):
                continue
            cls, elided, emphasis = explain(quote, rec, eforms, essay_words)
            counts["n"] += 1
            counts[cls] += 1
            if rec["category"] == vqc.ALTERED:
                counts["altered"] += 1
                counts["altered_elision"] += cls in ("elision", "elision_words")
            if cls != "word_changed":
                continue
            counts["wc_elided"] += elided
            if emphasis:
                counts["wc_emphasis"] += 1
                continue
            counts["wc_unmarked"] += 1
            if elided:
                continue
            counts["wc_unmarked_plain"] += 1
            kinds = change_kinds(rec)
            for kind in KINDS:
                counts["unmarked_" + kind] += kinds[kind]
            if field == "evaluation":
                out["review"].append({"quote": rec["quote"], "passage_words": rec["passage"], "kinds": kinds})
        out[field] = counts
    return out


def summarise(rows: list[dict], field: str, rng: random.Random | None = None, reps: int = REPS) -> dict:
    tot = dict.fromkeys(COUNT_KEYS, 0)
    for r in rows:
        for k in COUNT_KEYS:
            tot[k] += r[field][k]
    res: dict = {"counts": tot, "matched_by_step": {}, "measures": {}}
    cum = 0
    for s in STEPS:
        cum += tot[s]
        res["matched_by_step"][s] = cum / tot["n"] if tot["n"] else None
    for name, (nums, den) in MEASURES.items():
        pairs = [(sum(r[field][k] for k in nums), r[field][den]) for r in rows]
        m = {"value": audit.ratio(pairs), "denominator": sum(d for _, d in pairs)}
        if rng is not None:
            m["ci95"] = audit.boot_ratio(pairs, rng, reps)
        res["measures"][name] = m
    unmarked = tot["wc_unmarked_plain"]
    res["unmarked_kinds_share"] = {k: (tot["unmarked_" + k] / unmarked if unmarked else None) for k in KINDS}
    return res


def verdict(point: float | None, lo: float | None, hi: float | None, den: int, floor: int) -> str:
    if point is None or den < floor:
        return "underpowered (denominator below %d)" % floor
    ok = (lo is None or point >= lo) and (hi is None or point <= hi)
    return "held" if ok else "did not hold"


def predictions(summary: dict) -> dict:
    out = {}
    for pid, name, lo, hi in PREDICTIONS:
        m = summary["measures"][name]
        floor = FLOOR if MEASURES[name][1] == "n" else GROUP_FLOOR
        out[pid] = {"measure": name, "low": lo, "high": hi, "value": m["value"], "ci95": m.get("ci95"),
                    "verdict": verdict(m["value"], lo, hi, m["denominator"], floor)}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, help="dataset file, or a folder to search for --name")
    ap.add_argument("--name", default="glm47_final.jsonl")
    ap.add_argument("--out", required=True, help="explain.json path")
    ap.add_argument("--review-sample", help="write up to 30 unmarked changed-words pairs here (not for publication)")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="first N rows only (testing)")
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--plan", default="PLAN-1b.md")
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
            done = list(pool.imap(explain_row, rows, chunksize=16))
    else:
        done = [explain_row(r) for r in rows]
    del rows

    rng = random.Random(SEED)
    res: dict = {"rows": len(done), "records_read": read}
    for field in audit.FIELDS:
        res[field] = summarise(done, field, rng if field == "evaluation" else None, args.reps)
        c = res[field]["counts"]
        res[field]["consistent_with_audit1"] = (c["n"] == AUDIT1[field]["primary_matched"]
                                                and c["exact"] == AUDIT1[field]["exact"])
    res["predictions"] = predictions(res["evaluation"])
    res["dataset_file"] = os.path.basename(path)
    res["dataset_sha256"] = audit.sha256_file(path)
    res["audit_sha256"] = audit.sha256_file(audit.__file__)
    res["checker_sha256"] = audit.sha256_file(vqc.__file__)
    if os.path.isfile(args.plan):
        res["plan_sha256"] = audit.sha256_file(args.plan)
    res["python"] = sys.version.split()[0]

    if args.review_sample:
        candidates = [x for r in done for x in r["review"]]
        pick = random.Random(SEED + "-review").sample(candidates, min(30, len(candidates)))
        with open(args.review_sample, "w", encoding="utf-8") as fh:
            for x in pick:
                fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    ev = res["evaluation"]
    print(json.dumps({"rows": res["rows"], "n": ev["counts"]["n"],
                      "consistent_with_audit1": ev["consistent_with_audit1"],
                      "matched_by_step": ev["matched_by_step"],
                      "predictions": {k: v["verdict"] for k, v in res["predictions"].items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
