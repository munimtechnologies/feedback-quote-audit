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
"""audit: does a published dataset of AI essay feedback quote the student verbatim?

Part of feedback-quote-audit, by MV2 of Munim, Inc. Made with AI agents working in his name.

Reads one public dataset of AI-written feedback on student essays, finds every passage the
feedback puts in double quotation marks, and checks it against the text the model was given
with verbatim_quote_check (the same checker as feedback-commons and quote-check). Only
aggregate counts are written to results.json; no essay or feedback text is. The optional
review sample (--review-sample) holds a few short quote/passage pairs for a human check and
is never published. PREREG.md fixes the hypotheses, filters and verdict rules.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import random
import re
import statistics
import sys
from multiprocessing import Pool

import verbatim_quote_check as vqc

# Passages in "straight", “curly”, «guillemet» or „low-high“ double quotes, on one line.
QUOTE_RE = re.compile(
    r'"([^"\n]{1,400})"|“([^“”\n]{1,400})”|«([^«»\n]{1,400})»|„([^„“”\n]{1,400})[“”]'
)

# Words just before a quote that mark it as a suggested rewrite rather than the student's text.
CUE_RE = re.compile(
    r"(?i)(?:\binstead\b|\brewr[io]te|\brewritten\b|\brevis|\breplac|\bbetter\b|"
    r"\bcould\s+(?:write|say|use)\b|\bshould\s+(?:be|read|say)\b|\bchange[ds]?\b|\bcorrect|"
    r"\bimprov|\be\.g\.|\bfor example\b|\bsuch as\b|\bconsider\b|\btry\b|\bsuggest|"
    r"\balternative|\bversion\b|\bwould be\b|→|->|=>)"
)
CUE_WINDOW = 60  # characters before the opening quote mark, same line only

FIELDS = ("evaluation", "reasoning")
MATCHED = (vqc.EXACT, vqc.PUNCT_WHITESPACE, vqc.ALTERED)
MIN_WORDS = 4
SHORT_MAX_WORDS = 25  # sensitivity analysis: 4..25-word quotes only
FLOOR = 300  # matched quotes needed for a verdict
GROUP_FLOOR = 100
REPS = 10_000
SEED = "feedback-quote-audit-ielts-20261026"
LOW_BAND_MAX = 5.5
HIGH_BAND_MIN = 7.0


def extract_quotes(text: str) -> list[tuple[str, str]]:
    """(quote, context) for every double-quoted passage; context = up to CUE_WINDOW chars before it."""
    out = []
    for m in QUOTE_RE.finditer(text):
        quote = next(g for g in m.groups() if g is not None)
        start = m.start()
        line_start = text.rfind("\n", 0, start) + 1
        out.append((quote, text[max(line_start, start - CUE_WINDOW):start]))
    return out


def split_source(human: str) -> tuple[str, str, str]:
    """Split the model's input into (question, essay, mode) at the first blank line."""
    for sep, mode in (("\n\n", "blank_line"), ("\n", "newline")):
        i = human.find(sep)
        if i >= 0 and human[i:].strip():
            return human[:i], human[i + len(sep):], mode
    return "", human, "whole"


def best_window(src_words: list[str], q_words: list[str], slack: int = 2) -> tuple[int, int, float]:
    """(start, width, ratio) of the best-matching window; same search order as vqc._best_ratio."""
    m, n = len(q_words), len(src_words)
    best, best_i, best_w = 0.0, 0, 0
    if m == 0 or n == 0:
        return best_i, best_w, best
    matcher = difflib.SequenceMatcher(autojunk=False)
    matcher.set_seq2(q_words)
    for w in sorted({w for w in range(max(1, m - slack), m + slack + 1)}):
        for i in range(0, max(0, n - w) + 1):
            window = src_words[i:i + w]
            if not window:
                continue
            matcher.set_seq1(window)
            r = matcher.ratio()
            if r > best:
                best, best_i, best_w = r, i, w
                if best >= 1.0:
                    return best_i, best_w, best
    return best_i, best_w, best


def word_edits(window: list[str], q_words: list[str]) -> int:
    """Number of words added, dropped or changed between the source window and the quote."""
    sm = difflib.SequenceMatcher(None, window, q_words, autojunk=False)
    return sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal")


def classify(essay: str, essay_words: list[str], question: str, quote: str, context: str) -> dict:
    """One quote's record. Holds no text except 'quote'/'passage' on altered quotes (review only)."""
    res = vqc.check(essay, quote)
    cleaned = vqc.clean_quote(quote)
    q_words = vqc.words(cleaned)
    rec = {"category": res.category, "similarity": round(res.similarity, 4), "n_words": len(q_words),
           "cue": bool(CUE_RE.search(context)), "question": False, "edits": None}
    if res.category != vqc.EXACT and question:
        q_res = vqc.check(question, quote)
        rec["question"] = q_res.category in (vqc.EXACT, vqc.PUNCT_WHITESPACE)
    if res.category == vqc.ALTERED:
        i, w, _ = best_window(essay_words, q_words)
        rec["edits"] = word_edits(essay_words[i:i + w], q_words)
        rec["quote"] = cleaned
        rec["passage"] = " ".join(essay_words[i:i + w])
    return rec


def in_primary(rec: dict, max_words: int | None = None) -> bool:
    """Primary set: matched, at least MIN_WORDS words, no rewrite cue, not a quote of the question."""
    if rec["category"] not in MATCHED or rec["n_words"] < MIN_WORDS or rec["cue"] or rec["question"]:
        return False
    return max_words is None or rec["n_words"] <= max_words


def to_row(idx: int, rec: dict) -> dict:
    """Keep only the fields the audit needs; the model input is the first human turn (else 'topic')."""
    human = ""
    for turn in rec.get("conversation") or rec.get("conversations") or []:
        if (turn.get("from") or turn.get("role")) in ("human", "user"):
            human = turn.get("value") or turn.get("content") or ""
            break
    return {"idx": idx, "band": rec.get("band"), "generator": rec.get("generator"),
            "human": human or rec.get("topic") or "",
            "evaluation": rec.get("evaluation") or "", "reasoning": rec.get("reasoning") or ""}


def audit_row(row: dict) -> dict:
    question, essay, mode = split_source(row["human"])
    essay_words = vqc.words(essay)
    out = {"idx": row["idx"], "band": row["band"], "mode": mode, "essay_words": len(essay_words)}
    for field in FIELDS:
        out[field] = [classify(essay, essay_words, question, q, c) for q, c in extract_quotes(row[field])]
    return out


def iter_records(path: str):
    """Records from a JSON Lines file or a single JSON array, read in a stream."""
    with open(path, "r", encoding="utf-8-sig") as fh:
        head = fh.read(4096).lstrip()
        fh.seek(0)
        if head.startswith("["):
            yield from _iter_json_array(fh)
            return
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def _iter_json_array(fh, chunk: int = 1 << 20):
    dec = json.JSONDecoder()
    buf = fh.read(chunk)
    buf = buf[buf.index("[") + 1:]
    while True:
        buf = buf.lstrip(" \t\r\n,")
        while not buf:
            more = fh.read(chunk)
            if not more:
                return
            buf = more.lstrip(" \t\r\n,")
        if buf[0] == "]":
            return
        while True:
            try:
                obj, end = dec.raw_decode(buf)
                break
            except json.JSONDecodeError:
                more = fh.read(chunk)
                if not more:
                    raise
                buf += more
        yield obj
        buf = buf[end:]


def parse_band(band) -> float | None:
    if band is None:
        return None
    s = str(band).strip()
    if s.startswith("<"):
        return float(s[1:]) - 0.5 if s[1:] else None
    try:
        return float(s)
    except ValueError:
        return None


def _pct(sorted_vals: list[float], p: float) -> float:
    k = (len(sorted_vals) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def ratio(pairs: list[tuple[int, int]]) -> float | None:
    den = sum(d for _, d in pairs)
    return None if den == 0 else sum(n for n, _ in pairs) / den


def boot_ratio(pairs, rng: random.Random, reps: int = REPS) -> tuple[float, float] | None:
    """Percentile 95% CI of sum(num)/sum(den), resampling essays."""
    pairs = [p for p in pairs if p[1] > 0]
    if not pairs:
        return None
    stats = []
    for _ in range(reps):
        s = rng.choices(pairs, k=len(pairs))
        stats.append(sum(n for n, _ in s) / sum(d for _, d in s))
    stats.sort()
    return _pct(stats, 0.025), _pct(stats, 0.975)


def boot_group_diff(a, b, rng: random.Random, reps: int = REPS) -> tuple[float, float] | None:
    """95% CI of ratio(a) - ratio(b), two independent groups of essays."""
    a = [p for p in a if p[1] > 0]
    b = [p for p in b if p[1] > 0]
    if not a or not b:
        return None
    stats = []
    for _ in range(reps):
        sa = rng.choices(a, k=len(a))
        sb = rng.choices(b, k=len(b))
        stats.append(sum(n for n, _ in sa) / sum(d for _, d in sa) - sum(n for n, _ in sb) / sum(d for _, d in sb))
    stats.sort()
    return _pct(stats, 0.025), _pct(stats, 0.975)


def boot_paired_diff(quads, rng: random.Random, reps: int = REPS) -> tuple[float, float] | None:
    """95% CI of ratio(x) - ratio(y) on the same essays; quads = (num_x, den_x, num_y, den_y)."""
    quads = [q for q in quads if q[1] > 0 or q[3] > 0]
    if not quads:
        return None
    stats = []
    for _ in range(reps):
        s = rng.choices(quads, k=len(quads))
        dx, dy = sum(q[1] for q in s), sum(q[3] for q in s)
        if dx == 0 or dy == 0:
            continue
        stats.append(sum(q[0] for q in s) / dx - sum(q[2] for q in s) / dy)
    if not stats:
        return None
    stats.sort()
    return _pct(stats, 0.025), _pct(stats, 0.975)


def essay_counts(recs: list[dict], max_words: int | None = None) -> tuple[int, int, int]:
    """(exact, word-faithful, matched) among the essay's primary-set quotes."""
    prim = [r for r in recs if in_primary(r, max_words)]
    exact = sum(r["category"] == vqc.EXACT for r in prim)
    faithful = sum(r["category"] in (vqc.EXACT, vqc.PUNCT_WHITESPACE) for r in prim)
    return exact, faithful, len(prim)


def verdict_level(point: float | None, matched: int) -> str:
    if point is None or matched < FLOOR:
        return "underpowered (fewer than %d matched quotes)" % FLOOR
    return "H1 held (exact rate >= 95.0%)" if point >= 0.95 else "H1 did not hold (exact rate < 95.0%)"


def verdict_diff(ci, n_a: int, n_b: int, floor: int, label: str) -> str:
    if ci is None or n_a < floor or n_b < floor:
        return "underpowered (fewer than %d matched quotes in a group)" % floor
    lo, hi = ci
    if hi < 0:
        return "%s held (difference below zero)" % label
    if lo > 0:
        return "%s reversed (difference above zero)" % label
    return "no clear difference (%s not supported)" % label


def analyse(audits: list[dict], reps: int = REPS, seed: str = SEED) -> dict:
    rng = random.Random(seed)
    res: dict = {"rows": len(audits)}
    res["split_modes"] = dict(sorted(_count(a["mode"] for a in audits).items()))
    words = [a["essay_words"] for a in audits]
    res["essay_words_median"] = statistics.median(words) if words else None
    for field in FIELDS:
        allq = [r for a in audits for r in a[field]]
        f = {"quotes": len(allq), "essays_with_quotes": sum(1 for a in audits if a[field]),
             "categories_all": dict(sorted(_count(r["category"] for r in allq).items())),
             "excluded_cue": sum(r["cue"] for r in allq),
             "excluded_question": sum(r["question"] for r in allq),
             "under_min_words": sum(r["n_words"] < MIN_WORDS for r in allq)}
        prim = [r for r in allq if in_primary(r)]
        f["primary_matched"] = len(prim)
        f["primary_categories"] = dict(sorted(_count(r["category"] for r in prim).items()))
        edits = [r["edits"] for r in prim if r["category"] == vqc.ALTERED]
        f["altered_word_edits"] = dict(sorted(_count(min(e, 4) for e in edits).items()))
        ex_pairs = [(e, m) for e, _, m in (essay_counts(a[field]) for a in audits)]
        fa_pairs = [(fa, m) for _, fa, m in (essay_counts(a[field]) for a in audits)]
        sh_pairs = [(e, m) for e, _, m in (essay_counts(a[field], SHORT_MAX_WORDS) for a in audits)]
        unf = [[r for r in a[field] if r["category"] in MATCHED and r["n_words"] >= MIN_WORDS] for a in audits]
        unf_pairs = [(sum(r["category"] == vqc.EXACT for r in u), len(u)) for u in unf]
        f["exact_rate"] = ratio(ex_pairs)
        f["exact_rate_ci95"] = boot_ratio(ex_pairs, rng, reps)
        f["word_faithful_rate"] = ratio(fa_pairs)
        f["word_faithful_rate_ci95"] = boot_ratio(fa_pairs, rng, reps)
        f["exact_rate_4_to_25_words"] = ratio(sh_pairs)
        f["exact_rate_unfiltered"] = ratio(unf_pairs)
        f["unfiltered_matched"] = sum(m for _, m in unf_pairs)
        res[field] = f
    ev = res["evaluation"]
    res["H1"] = verdict_level(ev["exact_rate"], ev["primary_matched"])

    low = [essay_counts(a["evaluation"]) for a in audits
           if parse_band(a["band"]) is not None and parse_band(a["band"]) <= LOW_BAND_MAX]
    high = [essay_counts(a["evaluation"]) for a in audits
            if parse_band(a["band"]) is not None and parse_band(a["band"]) >= HIGH_BAND_MIN]
    low_p, high_p = [(e, m) for e, _, m in low], [(e, m) for e, _, m in high]
    n_low, n_high = sum(m for _, m in low_p), sum(m for _, m in high_p)
    ci2 = boot_group_diff(low_p, high_p, rng, reps)
    res["H2_band"] = {"low_band_essays": len(low), "high_band_essays": len(high),
                      "low_matched": n_low, "high_matched": n_high,
                      "low_exact_rate": ratio(low_p), "high_exact_rate": ratio(high_p),
                      "diff_low_minus_high": (None if ratio(low_p) is None or ratio(high_p) is None
                                              else ratio(low_p) - ratio(high_p)),
                      "diff_ci95": ci2,
                      "verdict": verdict_diff(ci2, n_low, n_high, GROUP_FLOOR, "H2")}

    quads = []
    for a in audits:
        er, _, mr = essay_counts(a["reasoning"])
        ee, _, me = essay_counts(a["evaluation"])
        quads.append((er, mr, ee, me))
    pr = ratio([(q[0], q[1]) for q in quads])
    pe = ratio([(q[2], q[3]) for q in quads])
    ci3 = boot_paired_diff(quads, rng, reps)
    res["H3_reasoning_vs_evaluation"] = {
        "reasoning_exact_rate": pr, "evaluation_exact_rate": pe,
        "diff_reasoning_minus_evaluation": None if pr is None or pe is None else pr - pe,
        "diff_ci95": ci3,
        "verdict": verdict_diff(ci3, sum(q[1] for q in quads), sum(q[3] for q in quads), FLOOR, "H3")}
    return res


def _count(items) -> dict:
    out: dict = {}
    for x in items:
        out[str(x)] = out.get(str(x), 0) + 1
    return out


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def find_file(root: str, name: str) -> str | None:
    """The file called `name` under root, else the largest file there (downloads may be renamed)."""
    biggest, size = None, -1
    for dirpath, _, files in os.walk(root):
        if name in files:
            return os.path.join(dirpath, name)
        for f in files:
            p = os.path.join(dirpath, f)
            if os.path.getsize(p) > size:
                biggest, size = p, os.path.getsize(p)
    return biggest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, help="dataset file, or a folder to search for --name")
    ap.add_argument("--name", default="glm47_final.jsonl")
    ap.add_argument("--out", required=True, help="results.json path")
    ap.add_argument("--review-sample", help="write up to 30 altered quote/passage pairs here (not for publication)")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="first N rows only (testing)")
    ap.add_argument("--prereg", default="PREREG.md")
    args = ap.parse_args(argv)

    path = args.data if os.path.isfile(args.data) else find_file(args.data, args.name)
    if not path:
        print("dataset file not found under %s" % args.data, file=sys.stderr)
        return 2
    rows, generators = [], {}
    for idx, rec in enumerate(iter_records(path)):
        if args.limit and idx >= args.limit:
            break
        row = to_row(idx, rec)
        generators[str(row["generator"])] = generators.get(str(row["generator"]), 0) + 1
        if row["human"].strip() and row["evaluation"].strip():
            rows.append(row)
    print("%d records read, %d usable" % (sum(generators.values()), len(rows)), file=sys.stderr)

    if args.workers > 1:
        with Pool(args.workers) as pool:
            audits = list(pool.imap(audit_row, rows, chunksize=16))
    else:
        audits = [audit_row(r) for r in rows]
    del rows

    res = analyse(audits)
    res["dataset_file"] = os.path.basename(path)
    res["dataset_sha256"] = sha256_file(path)
    res["records_read"] = sum(generators.values())
    res["generators"] = generators
    res["checker_sha256"] = sha256_file(vqc.__file__)
    if os.path.isfile(args.prereg):
        res["prereg_sha256"] = sha256_file(args.prereg)
    res["python"] = sys.version.split()[0]

    if args.review_sample:
        altered = [r for a in audits for r in a["evaluation"] if in_primary(r) and r["category"] == vqc.ALTERED]
        pick = random.Random(SEED + "-review").sample(altered, min(30, len(altered)))
        with open(args.review_sample, "w", encoding="utf-8") as fh:
            for r in pick:
                fh.write(json.dumps({"quote": r["quote"], "passage_words": r["passage"],
                                     "similarity": r["similarity"], "edits": r["edits"]},
                                    ensure_ascii=False) + "\n")
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    ev = res["evaluation"]
    print(json.dumps({"rows": res["rows"], "primary_matched": ev["primary_matched"],
                      "exact_rate": ev["exact_rate"], "ci95": ev["exact_rate_ci95"], "H1": res["H1"],
                      "H2": res["H2_band"]["verdict"], "H3": res["H3_reasoning_vs_evaluation"]["verdict"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
