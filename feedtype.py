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
"""feedtype: do six LLMs quote the student's own words in their essay feedback? (audit 4)

Part of feedback-quote-audit, by MV2 of Munim, Inc. Made with AI agents working in his name.

Audits 1-3 checked one model (GLM-4.7) on one exam (IELTS). This pass, fixed in PLAN-4.md before
it ran, applies the same quote filters and classes (it imports audit.py and explain.py) to the
FeedType benchmark (Almousa et al., AIME-Con 2026; github.com/nia135/FeedType at a pinned commit):
paragraph-level feedback from six LLMs under three prompts on real first-year university essays
from the SEFORA corpus, with the teachers' own comments alongside. For every passage a model's
comment puts in double quotation marks it asks whether the student's words were kept, whether a
changed quote is a close (tight) or loose match, and whether a faithful quote came from the
paragraph being discussed or from elsewhere in the essay. The repository tarball is read in
memory and never extracted. Only aggregate counts are written; no essay or feedback text is.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tarfile
from multiprocessing import Pool

import audit
import explain
import verbatim_quote_check as vqc

COMMIT = "ad955eca067ce5eeff12eddc309bfbcb83e63439"  # nia135/FeedType, 2026-09-22
TIGHT = 0.8  # best-match similarity at or above which a changed quote is a close (tight) copy
SHORT = (4, 6)  # quote length in words, inclusive, for the short stratum
LONG_MIN = 11  # long stratum: 11 words or more (audit 3's strata; 7-10 is a gap)
SMALL = ("LLaMa8B", "Mistral7B")  # folder names in FeedType/Models
LARGE = ("Mistral24B", "Qwen70B", "Gemini2Flash", "LearnLM")
MODELS = SMALL + LARGE
KEYS = ("comments", "comments_quoting", "quotes", "excluded_cue", "excluded_teacher", "under_min_words",
        "not_found", "n", "wc", "prim_tight", "wc_tight", "wc_loose", "faithful", "faithful_elsewhere",
        "n_short", "wc_short", "n_long", "wc_long")
# name: (numerator key, denominator key)
RATES = {"word_changed_rate": ("wc", "n"),
         "loose_share_of_changed": ("wc_loose", "wc"),
         "elsewhere_share_of_faithful": ("faithful_elsewhere", "faithful"),
         "quoting_comment_share": ("comments_quoting", "comments")}

REPS = 10_000
SEED = "feedback-quote-audit-4-20261029"
FLOOR = 300  # primary-set quotes needed for the pooled verdict (C1)
GROUP_FLOOR = 100  # quotes needed in each side of a comparison (C2, C3)
WC_MAX = 0.05  # C1 holds if the pooled word-changed rate is at most this (audit 1b's P3 bound)


def locate(path: str) -> tuple[str, str, str, str] | None:
    """(kind, model, prompt, draft) for a FeedType JSON file inside the tarball, else None."""
    parts = path.replace("\\", "/").split("/")
    name = parts[-1]
    if not name.endswith(".json") or name.startswith("._"):
        return None
    for i in range(len(parts) - 2):
        if parts[i] != "FeedType":
            continue
        if parts[i + 1] == "Models" and i + 4 < len(parts):
            return "model", parts[i + 2], parts[i + 3], name[:-5]
        if parts[i + 1] == "Teacher":
            return "teacher", "Teacher", "", name[:-5]
    return None


def feedback_text(ann: dict, kind: str) -> str | None:
    """The comment an annotation contributes for this kind of file, else None."""
    if kind == "model":
        return (ann.get("model_comment") or "") if ann.get("type") == "model_feedback" else None
    if ann.get("type") in ("note", "highlight") and (ann.get("comment") or "").strip():
        return ann["comment"]
    return None


def in_paragraph(quote: str, body: str) -> bool:
    """True if a word-faithful quote is found in this paragraph (same steps as explain.explain)."""
    if explain.first_step(quote, explain.essay_forms(body)) is not None:
        return True
    if vqc.check(body, quote).category in (vqc.EXACT, vqc.PUNCT_WHITESPACE):
        return True
    plain = vqc.clean_quote(quote).translate(explain.TYPOGRAPHY)
    pieces = [w for w in (vqc.words(p) for p in explain.ELLIPSIS_RE.split(plain)) if w]
    return len(pieces) > 1 and explain.words_in_order(pieces, vqc.words(body))


def tally(c: dict, quote: str, rec: dict, body: str, eforms: list[str], essay_words: list[str]) -> bool:
    """Add one quote to the counts; True if it is in the primary set."""
    c["quotes"] += 1
    c["under_min_words"] += rec["n_words"] < audit.MIN_WORDS
    c["excluded_cue"] += rec["cue"]
    c["excluded_teacher"] += rec["question"]
    c["not_found"] += rec["category"] == vqc.NOT_FOUND
    if not audit.in_primary(rec):
        return False
    cls = explain.explain(quote, rec, eforms, essay_words)[0]
    tight = rec["similarity"] >= TIGHT
    short = SHORT[0] <= rec["n_words"] <= SHORT[1]
    long_ = rec["n_words"] >= LONG_MIN
    c["n"] += 1
    c["prim_tight"] += tight
    c["n_short"] += short
    c["n_long"] += long_
    if cls == "word_changed":
        c["wc"] += 1
        c["wc_tight"] += tight
        c["wc_loose"] += not tight
        c["wc_short"] += short
        c["wc_long"] += long_
    else:
        c["faithful"] += 1
        c["faithful_elsewhere"] += not in_paragraph(quote, body)
    return True


def file_counts(doc: dict, kind: str) -> dict:
    """Counts for one essay draft. A model comment's quote of the teacher's comments is set aside."""
    paras = [p for p in doc.get("paragraphs") or [] if isinstance(p, dict)]
    bodies = [p.get("body") or "" for p in paras]
    essay = "\n\n".join(bodies)
    essay_words = vqc.words(essay)
    eforms = explain.essay_forms(essay)
    notes = [feedback_text(a, "teacher") for p in paras for a in p.get("annotations") or []]
    teacher = "" if kind == "teacher" else "\n".join(t for t in notes if t)
    c = dict.fromkeys(KEYS, 0)
    for body, p in zip(bodies, paras):
        for ann in p.get("annotations") or []:
            comment = feedback_text(ann, kind)
            if comment is None:
                continue
            c["comments"] += 1
            primary = 0
            for quote, context in audit.extract_quotes(comment):
                rec = audit.classify(essay, essay_words, teacher, quote, context)
                primary += tally(c, quote, rec, body, eforms, essay_words)
            c["comments_quoting"] += primary > 0
    return c


def process(item: tuple) -> dict:
    kind, model, prompt, draft, raw = item
    out = {"kind": kind, "model": model, "prompt": prompt, "draft": draft}
    try:
        doc = json.loads(raw.decode("utf-8-sig"))
    except ValueError:
        out["error"] = True
        return out
    out["counts"] = file_counts(doc if isinstance(doc, dict) else {}, kind)
    return out


def read_items(path: str) -> tuple[list[tuple], list[str]]:
    """FeedType JSON files from the tarball, read in memory (never extracted); and the root folders."""
    items, roots = [], set()
    with tarfile.open(path, "r:*") as tar:
        for m in tar:
            roots.add(m.name.split("/")[0])
            if not m.isfile():
                continue
            loc = locate(m.name)
            if loc is None:
                continue
            fh = tar.extractfile(m)
            if fh is not None:
                items.append(loc + (fh.read(),))
    return items, sorted(roots)


def total(results: list[dict], pred) -> dict:
    t = dict.fromkeys(KEYS, 0)
    for r in results:
        if pred(r):
            for k in KEYS:
                t[k] += r["counts"][k]
    return t


def per_draft(results: list[dict], pred, num: str, den: str) -> list[tuple[int, int]]:
    """(numerator, denominator) per essay draft, summed over the selected files."""
    d: dict = {}
    for r in results:
        if pred(r):
            a = d.setdefault(r["draft"], [0, 0])
            a[0] += r["counts"][num]
            a[1] += r["counts"][den]
    return [tuple(v) for _, v in sorted(d.items())]


def paired(results: list[dict], side_a: tuple, side_b: tuple) -> list[tuple[int, int, int, int]]:
    """(num_a, den_a, num_b, den_b) per essay draft; each side = (pred, num key, den key)."""
    d: dict = {}
    for r in results:
        for j, (pred, num, den) in enumerate((side_a, side_b)):
            if pred(r):
                q = d.setdefault(r["draft"], [0, 0, 0, 0])
                q[2 * j] += r["counts"][num]
                q[2 * j + 1] += r["counts"][den]
    return [tuple(v) for _, v in sorted(d.items())]


def summary(results: list[dict], pred, rng: random.Random | None, reps: int) -> dict:
    out: dict = {"counts": total(results, pred), "drafts": len({r["draft"] for r in results if pred(r)})}
    for name, (num, den) in RATES.items():
        pairs = per_draft(results, pred, num, den)
        out[name] = audit.ratio(pairs)
        if rng is not None and name == "word_changed_rate":
            out[name + "_ci95"] = audit.boot_ratio(pairs, rng, reps)
    return out


def verdict_sign(ci, den_a: int, den_b: int, floor: int, labels: tuple[str, str]) -> str:
    """Verdict on the 95% CI of (rate a - rate b); the plan predicts a higher."""
    if ci is None or den_a < floor or den_b < floor:
        return "underpowered (fewer than %d quotes on a side)" % floor
    lo, hi = ci
    if lo > 0:
        return "held (%s higher)" % labels[0]
    if hi < 0:
        return "reversed (%s higher)" % labels[1]
    return "no clear difference"


def diff_test(quads, labels: tuple[str, str], measure: str, rng: random.Random, reps: int) -> dict:
    a = audit.ratio([(q[0], q[1]) for q in quads])
    b = audit.ratio([(q[2], q[3]) for q in quads])
    ci = audit.boot_paired_diff(quads, rng, reps)
    den_a, den_b = sum(q[1] for q in quads), sum(q[3] for q in quads)
    return {"measure": measure, labels[0]: a, labels[1]: b,
            "diff": None if a is None or b is None else a - b, "diff_ci95": ci,
            "denominators": [den_a, den_b], "verdict": verdict_sign(ci, den_a, den_b, GROUP_FLOOR, labels)}


def analyse(results: list[dict], reps: int = REPS, seed: str = SEED) -> dict:
    rng = random.Random(seed)
    ok = [r for r in results if not r.get("error")]
    model = [r for r in ok if r["kind"] == "model"]
    teacher = [r for r in ok if r["kind"] == "teacher"]
    names = sorted({r["model"] for r in model})
    cells = sorted({(r["model"], r["prompt"]) for r in model})
    res: dict = {"files": len(results), "parse_errors": len(results) - len(ok),
                 "model_files": len(model), "teacher_files": len(teacher),
                 "unexpected_models": [m for m in names if m not in MODELS],
                 "missing_models": [m for m in MODELS if m not in names]}
    res["pooled"] = summary(model, lambda r: True, rng, reps)
    res["by_model"] = {m: summary(model, lambda r, m=m: r["model"] == m, rng, reps) for m in names}
    res["by_prompt"] = {p: summary(model, lambda r, p=p: r["prompt"] == p, rng, reps)
                        for p in sorted({r["prompt"] for r in model})}
    res["by_cell"] = {"%s / %s" % c: summary(model, lambda r, c=c: (r["model"], r["prompt"]) == c, None, reps)
                      for c in cells}
    res["teacher"] = summary(teacher, lambda r: True, rng, reps)

    p = res["pooled"]
    tests: dict = {"C1_pooled_word_changed": {
        "measure": "word-changed rate among primary-set quotes, all six models and three prompts",
        "high": WC_MAX, "value": p["word_changed_rate"], "ci95": p["word_changed_rate_ci95"],
        "denominator": p["counts"]["n"],
        "verdict": explain.verdict(p["word_changed_rate"], None, WC_MAX, p["counts"]["n"], FLOOR)}}
    quads = paired(model, (lambda r: r["model"] in SMALL, "wc", "n"), (lambda r: r["model"] in LARGE, "wc", "n"))
    tests["C2_small_vs_large"] = diff_test(
        quads, ("small models", "larger models"),
        "word-changed rate, LLaMA-3.1 8B + Mistral-7B minus the four larger models (paired by draft)", rng, reps)
    quads = paired(model, (lambda r: True, "wc_short", "n_short"), (lambda r: True, "wc_long", "n_long"))
    tests["C3_short_vs_long"] = diff_test(
        quads, ("short quotes", "long quotes"),
        "word-changed rate, 4-6-word quotes minus 11+-word quotes, all models (paired by draft)", rng, reps)
    res["tests"] = tests
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", required=True, help="the FeedType tarball, or a folder holding it")
    ap.add_argument("--name", default="feedtype.tar.gz")
    ap.add_argument("--out", required=True, help="feedtype.json path")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--plan", default="PLAN-4.md")
    args = ap.parse_args(argv)

    path = args.data if os.path.isfile(args.data) else audit.find_file(args.data, args.name)
    if not path:
        print("tarball not found under %s" % args.data, file=sys.stderr)
        return 2
    items, roots = read_items(path)
    print("%d FeedType files read from %s" % (len(items), os.path.basename(path)), file=sys.stderr)

    if args.workers > 1:
        with Pool(args.workers) as pool:
            done = list(pool.imap(process, items, chunksize=8))
    else:
        done = [process(i) for i in items]
    del items

    res = analyse(done, args.reps)
    res["commit"] = COMMIT
    res["tar_roots"] = roots
    res["commit_in_root"] = any(COMMIT in r for r in roots)
    res["tar_sha256"] = audit.sha256_file(path)
    res["audit_sha256"] = audit.sha256_file(audit.__file__)
    res["explain_sha256"] = audit.sha256_file(explain.__file__)
    res["checker_sha256"] = audit.sha256_file(vqc.__file__)
    if os.path.isfile(args.plan):
        res["plan_sha256"] = audit.sha256_file(args.plan)
    res["python"] = sys.version.split()[0]

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print(json.dumps({"model_files": res["model_files"], "teacher_files": res["teacher_files"],
                      "n": res["pooled"]["counts"]["n"], "commit_in_root": res["commit_in_root"],
                      "verdicts": {k: v["verdict"] for k, v in res["tests"].items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
