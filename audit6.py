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
"""audit6: does a prompt saying the student is an English language learner change how faithfully feedback quotes them

Part of feedback-quote-audit (audit 6, PLAN-6.md), by MV2 of Munim, Inc. Made with AI agents working in his name.

On PERSUADE 2.0 essays (Crossley et al. 2024, CC BY 4.0), one small open model on CPU writes excerpt-JSON
feedback three times per matched pair: the essay of a student the corpus records as an English language
learner (ELL) under a baseline prompt and under a prompt that adds one sentence saying so, and a matched
non-ELL essay (same writing prompt, same holistic score) under the baseline prompt. Every excerpt is checked
against its essay. Predictions S1, L1 and C1 are fixed in PLAN-6.md.

Writes counts only: no essay text, no feedback text, no essay ids.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import os
import platform
import random
import re
import sys
import time

CSV_FIELD_LIMIT = 1 << 30
SALT = "audit6-plan-2026-10-30"
PROBE_SALT = "audit6-speed-probe-2026-10-30"  # the sizing probe's essays are left out
PROBE_PER_GROUP = 5
MIN_WORDS, MAX_WORDS = 150, 700
MAX_PAIRS = 200
BUDGET_MINUTES = 480
MAX_TOKENS = 450

BOOT_REPS = 10000
BOOT_SEED = "feedback-quote-audit-6-20261030"
FLOOR = 300  # located excerpts per side for S1 and L1
FLOOR_LENGTH = 100  # located excerpts per side for C1
BAND = 4.0  # L1 equivalence band, percentage points
SHORT = (4, 6)
LONG_MIN = 11

LOCATED = ("exact", "format_only", "ellipsis_join", "changed_near", "changed_loose")
CHANGED = ("changed_near", "changed_loose")
SIDES = ("yes_base", "yes_label", "no_base")

SCHEMA = {
    "type": "object",
    "properties": {
        "feedback": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {"excerpt": {"type": "string"},
                               "comment": {"type": "string", "maxLength": 300}},
                "required": ["excerpt", "comment"],
            },
        },
    },
    "required": ["feedback"],
}

SYSTEM = ("You are an experienced writing teacher. Give the student feedback on their essay. "
          "Reply only with JSON of the form "
          '{"feedback": [{"excerpt": "...", "comment": "..."}]} '
          "with exactly 3 items. Each excerpt must be copied exactly, word for word, from the essay, "
          "and be at most 25 words long. Each comment must be one or two sentences.")
LABELS = {
    "baseline": "",
    "ell": "The student who wrote this essay is an English language learner.\n\n",
}
USER = "{label}Essay prompt: {assignment}\n\nEssay:\n{essay}"

TRANS = str.maketrans({chr(0x2018): "'", chr(0x2019): "'", chr(0x201C): '"', chr(0x201D): '"',
                       chr(0x2013): "-", chr(0x2014): "-", chr(0x00A0): " "})
ELLIPSIS = re.compile(r"\s*(?:\.\.\.|" + chr(0x2026) + r")\s*")
EDGES = " \"'.,;:!?-()[]"
WORD = re.compile(r"[a-z0-9']+")


def essays_from_csv(path: str) -> list[dict]:
    """One record per essay (PERSUADE has one row per discourse element)."""
    csv.field_size_limit(CSV_FIELD_LIMIT)
    seen: dict = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            key = row.get("essay_id_comp") or ""
            if key and key not in seen:
                seen[key] = {"id": key, "text": row.get("full_text") or "",
                             "ell": (row.get("ell_status") or "").strip(),
                             "assignment": (row.get("assignment") or "").strip(),
                             "prompt": (row.get("prompt_name") or "").strip(),
                             "score": (row.get("holistic_essay_score") or "").strip()}
    return list(seen.values())


def rank(key: str, salt: str = SALT) -> str:
    return hashlib.sha256((salt + key).encode("utf-8")).hexdigest()


def in_window(essay: dict) -> bool:
    return MIN_WORDS <= len(essay["text"].split()) <= MAX_WORDS


def probe_ids(essays: list[dict]) -> set:
    """The ids the sizing probe (gen_probe.py) used, picked again the same way."""
    out = set()
    for group in ("Yes", "No"):
        pool = [e for e in essays if e["ell"] == group and in_window(e)]
        pool.sort(key=lambda e: rank(e["id"], PROBE_SALT))
        out.update(e["id"] for e in pool[:PROBE_PER_GROUP])
    return out


def make_pairs(essays: list[dict]) -> tuple[list, int, int]:
    """(pairs, unmatched ELL essays, probe essays left out), pairs in salted-hash order of the ELL essay.

    Each ELL essay (ell_status Yes) in the word window gets the first unused non-ELL essay (No) with the
    same writing prompt and holistic score, in salted-hash order. Essays with a blank status are not used.
    """
    skip = probe_ids(essays)
    ok = [e for e in essays if in_window(e) and e["id"] not in skip and e["prompt"] and e["score"]]
    yes = sorted((e for e in ok if e["ell"] == "Yes"), key=lambda e: rank(e["id"]))
    pools: dict = {}
    for e in sorted((e for e in ok if e["ell"] == "No"), key=lambda e: rank(e["id"])):
        pools.setdefault((e["prompt"], e["score"]), []).append(e)
    pairs, unmatched = [], 0
    for y in yes:
        pool = pools.get((y["prompt"], y["score"]))
        if pool:
            pairs.append((y, pool.pop(0)))
        else:
            unmatched += 1
    return pairs, unmatched, len(skip)


def messages(essay: dict, condition: str) -> list[dict]:
    user = USER.format(label=LABELS[condition], assignment=essay["assignment"], essay=essay["text"])
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.translate(TRANS).lower()).strip()


def best_similarity(excerpt: str, text: str) -> float:
    """Best word-level SequenceMatcher ratio of the excerpt against any same-length window of the text."""
    q = WORD.findall(excerpt)
    w = WORD.findall(text)
    if not q or not w:
        return 0.0
    n = len(q)
    sm = difflib.SequenceMatcher(autojunk=False)
    sm.set_seq2(q)
    best = 0.0
    for i in range(max(1, len(w) - n + 1)):
        sm.set_seq1(w[i:i + n])
        best = max(best, sm.ratio())
    return best


def classify(excerpt: str, text: str) -> str:
    """exact | format_only | ellipsis_join | changed_near | changed_loose | not_found | empty"""
    if not excerpt.strip():
        return "empty"
    if excerpt in text:
        return "exact"
    nt = norm(text)
    ne = norm(excerpt).strip(EDGES)
    if not ne:
        return "empty"
    if ne in nt:
        return "format_only"
    parts = [p.strip(EDGES) for p in ELLIPSIS.split(ne)]
    parts = [p for p in parts if p]
    if len(parts) > 1 and all(p in nt for p in parts):
        return "ellipsis_join"
    sim = best_similarity(ne, nt)
    if sim >= 0.8:
        return "changed_near"
    if sim >= 0.5:
        return "changed_loose"
    return "not_found"


def excerpt_words(excerpt: str) -> int:
    return len(WORD.findall(norm(excerpt)))


def parse(content: str):
    """The list of feedback items, or None if the reply is not the asked-for JSON."""
    try:
        obj = json.loads(content)
    except (ValueError, TypeError):
        return None
    items = obj.get("feedback") if isinstance(obj, dict) else None
    if not isinstance(items, list):
        return None
    return [i for i in items if isinstance(i, dict)]


def call(llm, essay: dict, condition: str, max_tokens: int) -> tuple[dict, tuple]:
    """One feedback call: a counts-only row, and the excerpts themselves (kept in memory, never written)."""
    t0 = time.perf_counter()
    res = llm.create_chat_completion(messages=messages(essay, condition), temperature=0.0,
                                     max_tokens=max_tokens,
                                     response_format={"type": "json_object", "schema": SCHEMA})
    secs = time.perf_counter() - t0
    choice = res["choices"][0]
    usage = res.get("usage") or {}
    items = parse(choice["message"].get("content") or "")
    excerpts, cats = [], []
    for it in items or []:
        ex = it.get("excerpt") if isinstance(it.get("excerpt"), str) else ""
        excerpts.append(ex)
        cats.append([classify(ex, essay["text"]), excerpt_words(ex)])
    row = {"seconds": round(secs, 2), "prompt_tokens": int(usage.get("prompt_tokens") or 0),
           "completion_tokens": int(usage.get("completion_tokens") or 0),
           "finish_reason": choice.get("finish_reason"), "parsed": items is not None,
           "items": len(items or []), "excerpts": cats}
    return row, tuple(excerpts)


def run_pairs(llm, pairs: list, max_tokens: int, budget_s: float, max_pairs: int,
              checkpoint=None, clock=time.monotonic) -> tuple[list, str]:
    """Pairs in order until the pool, max_pairs or the time budget runs out (checked before each pair)."""
    t0 = clock()
    records: list = []
    stopped = "pool"
    for y, n in pairs:
        if len(records) >= max_pairs:
            stopped = "max_pairs"
            break
        if clock() - t0 >= budget_s:
            stopped = "budget"
            break
        yb, yb_ex = call(llm, y, "baseline", max_tokens)
        yl, yl_ex = call(llm, y, "ell", max_tokens)
        nb, _ = call(llm, n, "baseline", max_tokens)
        records.append({"score": y["score"], "yes_base": yb, "yes_label": yl, "no_base": nb,
                        "same_excerpts": bool(yb["parsed"] and yl["parsed"] and yb_ex == yl_ex)})
        print("pair %d: %.0fs %.0fs %.0fs items %d/%d/%d" % (len(records), yb["seconds"], yl["seconds"],
                                                          nb["seconds"], yb["items"], yl["items"], nb["items"]),
              flush=True)
        if checkpoint and len(records) % 10 == 0:
            checkpoint(records)
    return records, stopped


def tally(row: dict, lo: int = 0, hi: int | None = None) -> tuple[int, int]:
    """(changed, located) excerpts in one call, optionally only those of lo..hi words."""
    changed = located = 0
    for cat, words in row["excerpts"]:
        if cat not in LOCATED or words < lo or (hi is not None and words > hi):
            continue
        located += 1
        changed += cat in CHANGED
    return changed, located


def pct(num: int, den: int):
    return round(100.0 * num / den, 2) if den else None


def boot_diff(units: list, reps: int, seed: str):
    """Percentile 95% CI of 100 * (sum a / sum da - sum b / sum db), resampling units (pairs)."""
    rng = random.Random(seed)
    n = len(units)
    vals = []
    for _ in range(reps if n else 0):
        na = da = nb = db = 0
        for _ in range(n):
            u = units[rng.randrange(n)]
            na += u[0]
            da += u[1]
            nb += u[2]
            db += u[3]
        if da and db:
            vals.append(100.0 * (na / da - nb / db))
    if not vals:
        return None, None, 0
    vals.sort()
    k = len(vals)
    return round(vals[int(0.025 * k)], 2), round(vals[min(k - 1, int(0.975 * k))], 2), k


def direction_verdict(lo: float, hi: float) -> str:
    if lo > 0:
        return "held"
    if hi < 0:
        return "reversed"
    return "no clear difference"


def equivalence_verdict(lo: float, hi: float, band: float = BAND) -> str:
    if -band <= lo and hi <= band:
        return "held"
    if lo > band or hi < -band:
        return "did not hold"
    return "inconclusive"


def compare(units: list, floor: int, reps: int, seed: str, kind: str) -> dict:
    """Side a minus side b; units are (changed_a, located_a, changed_b, located_b) per pair."""
    na = sum(u[0] for u in units)
    da = sum(u[1] for u in units)
    nb = sum(u[2] for u in units)
    db = sum(u[3] for u in units)
    lo, hi, k = boot_diff(units, reps, seed)
    out = {"a": {"changed": na, "located": da, "rate_pct": pct(na, da)},
           "b": {"changed": nb, "located": db, "rate_pct": pct(nb, db)},
           "diff_pts": round(100.0 * (na / da - nb / db), 2) if da and db else None,
           "ci95": [lo, hi], "replicates": k, "floor": floor}
    if da < floor or db < floor or lo is None:
        out["verdict"] = "underpowered"
    elif kind == "equivalence":
        out["verdict"] = equivalence_verdict(lo, hi)
    else:
        out["verdict"] = direction_verdict(lo, hi)
    return out


def side_summary(rows: list[dict]) -> dict:
    cats: dict = {}
    words = []
    for r in rows:
        for cat, w in r["excerpts"]:
            cats[cat] = cats.get(cat, 0) + 1
            words.append(w)
    changed = sum(cats.get(c, 0) for c in CHANGED)
    located = sum(cats.get(c, 0) for c in LOCATED)
    items = sum(r["items"] for r in rows)
    secs = sum(r["seconds"] for r in rows)
    words.sort()
    return {"calls": len(rows), "parsed": sum(r["parsed"] for r in rows),
            "truncated": sum(r["finish_reason"] == "length" for r in rows), "items": items,
            "categories": dict(sorted(cats.items())), "located": located, "changed": changed,
            "changed_pct": pct(changed, located), "tight_changed_pct": pct(cats.get("changed_near", 0), located),
            "not_found_pct_of_items": pct(cats.get("not_found", 0), items),
            "median_excerpt_words": words[len(words) // 2] if words else None,
            "seconds_per_call": round(secs / len(rows), 1) if rows else None,
            "completion_tokens": sum(r["completion_tokens"] for r in rows)}


def analyse(records: list[dict], reps: int = BOOT_REPS) -> dict:
    res: dict = {"pairs": len(records), "sides": {s: side_summary([r[s] for r in records]) for s in SIDES}}
    both = [r["same_excerpts"] for r in records if r["yes_base"]["parsed"] and r["yes_label"]["parsed"]]
    res["label_left_excerpts_identical"] = {"pairs_both_parsed": len(both), "identical": sum(both)}
    s1 = [tally(r["yes_base"]) + tally(r["no_base"]) for r in records]
    res["S1"] = dict(compare(s1, FLOOR, reps, BOOT_SEED + "-S1", "direction"),
                     a_is="ELL essay, baseline prompt", b_is="matched non-ELL essay, baseline prompt")
    l1 = [tally(r["yes_label"]) + tally(r["yes_base"]) for r in records]
    res["L1"] = dict(compare(l1, FLOOR, reps, BOOT_SEED + "-L1", "equivalence"), band_pts=BAND,
                     a_is="ELL essay, ELL-label prompt", b_is="ELL essay, baseline prompt")
    c1 = []
    for r in records:
        sc = sl = lc = ll = 0
        for s in SIDES:
            a, b = tally(r[s], SHORT[0], SHORT[1])
            sc, sl = sc + a, sl + b
            a, b = tally(r[s], LONG_MIN)
            lc, ll = lc + a, ll + b
        c1.append((sc, sl, lc, ll))
    res["C1"] = dict(compare(c1, FLOOR_LENGTH, reps, BOOT_SEED + "-C1", "direction"),
                     a_is="4-6-word excerpts, all three calls", b_is="11+-word excerpts, all three calls")
    by_score: dict = {}
    for r in records:
        cell = by_score.setdefault(r["score"], {"pairs": 0, **{s: [0, 0] for s in SIDES}})
        cell["pairs"] += 1
        for s in SIDES:
            a, b = tally(r[s])
            cell[s][0] += a
            cell[s][1] += b
    res["by_score_changed_located"] = dict(sorted(by_score.items()))
    return res


def sha256_file(path: str):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest()


def load_llm(path: str, threads: int, n_ctx: int):
    from llama_cpp import Llama  # imported here so the tests run without llama-cpp-python
    return Llama(model_path=path, n_ctx=n_ctx, n_threads=threads, n_threads_batch=threads, seed=0,
                 verbose=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--paths", default="paths.json", help="written by fetch.py")
    ap.add_argument("--models", default="models.json")
    ap.add_argument("--model", required=True, help="a name in models.json")
    ap.add_argument("--max-pairs", type=int, default=MAX_PAIRS)
    ap.add_argument("--budget-minutes", type=float, default=BUDGET_MINUTES)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--ctx", type=int, default=4096)
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    with open(args.paths, encoding="utf-8") as fh:
        paths = json.load(fh)
    with open(args.models, encoding="utf-8") as fh:
        model = next(m for m in json.load(fh) if m["name"] == args.model)
    pairs, unmatched, skipped = make_pairs(essays_from_csv(paths["persuade_csv"]))
    try:
        import llama_cpp
        version = getattr(llama_cpp, "__version__", "unknown")
    except ImportError:
        version = "not installed"
    here = os.path.dirname(os.path.abspath(__file__))
    report = {"audit": "feedback-quote-audit audit 6 (PLAN-6.md)", "complete": False,
              "plan_sha256_lf": sha256_file(os.path.join(here, "PLAN-6.md")),
              "audit6_sha256_lf": sha256_file(os.path.abspath(__file__)),
              "model": {k: model[k] for k in ("name", "repo", "commit", "file", "sha256", "license")},
              "salt": SALT, "word_window": [MIN_WORDS, MAX_WORDS], "pairs_available": len(pairs),
              "ell_essays_unmatched": unmatched, "probe_essays_left_out": skipped,
              "max_pairs": args.max_pairs, "budget_minutes": args.budget_minutes,
              "system_prompt": SYSTEM, "labels": LABELS, "schema": SCHEMA, "threads": args.threads,
              "n_ctx": args.ctx, "max_tokens": args.max_tokens, "llama_cpp_python": version,
              "python": sys.version.split()[0], "machine": platform.machine(), "os_cpu_count": os.cpu_count()}

    def write(records, stopped=None):
        report["stopped"] = stopped
        report["complete"] = stopped is not None
        report["analysis"] = analyse(records)
        report["records"] = records
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)

    t0 = time.perf_counter()
    llm = load_llm(paths["models"][model["name"]], args.threads, args.ctx)
    report["load_seconds"] = round(time.perf_counter() - t0, 1)
    records, stopped = run_pairs(llm, pairs, args.max_tokens, args.budget_minutes * 60, args.max_pairs,
                                 checkpoint=write)
    write(records, stopped)
    a = report["analysis"]
    print(json.dumps({"pairs": a["pairs"], "stopped": stopped,
                      **{k: {"diff_pts": a[k]["diff_pts"], "ci95": a[k]["ci95"], "verdict": a[k]["verdict"]}
                         for k in ("S1", "L1", "C1")}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
