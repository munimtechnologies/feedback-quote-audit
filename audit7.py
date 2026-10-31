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
"""audit7: a powered re-test of audit 6 (does an "English language learner" prompt change how faithfully feedback quotes the student?)

Part of feedback-quote-audit (audit 7, PLAN-7.md), by MV2 of Munim, Inc. Made with AI agents working in his name.

Runs audit 6's own code (audit6.py, SHA-256 checked) on the matched PERSUADE 2.0 pairs audit 6 did not reach,
with Qwen2.5-1.5B only and a token limit of 800 instead of 450. The pairs are split into four disjoint shards,
one sealed CPU job each (`run`); `pool` joins the finished shard reports and judges the predictions in
PLAN-7.md (S1, L1, T1).

Writes counts only: no essay text, no feedback text, no essay ids.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time

import audit6 as a6

AUDIT = "feedback-quote-audit audit 7 (PLAN-7.md)"
AUDIT6_SHA_LF = "bb582d88a058c02a30ff06fedbea4b0b97ea48a51b279f9328d9fd23379f63fb"
SALT = "audit6-plan-2026-10-30"  # audit 7 keeps audit 6's pairs and their order
PAIRS_AVAILABLE = 1179
SHARDS = {1: (147, 306), 2: (307, 466), 3: (467, 626), 4: (627, 786)}  # 1-based pair numbers, inclusive
MODEL = "qwen2.5-1.5b-instruct-q4_k_m"
MAX_TOKENS = 800
BUDGET_MINUTES = 480

BOOT_REPS = 10000
BOOT_SEED = "feedback-quote-audit-7-20261031"
FLOOR = 600  # located excerpts per side for S1 and L1
FLOOR_T1 = 150  # located excerpts per side for T1
LONG_REPLY = 450  # T1: replies of more output tokens than this are "long" (audit 6's limit)
LENGTH_BANDS = ((1, 3), (4, 6), (7, 10), (11, 25), (26, None))


def check_audit6() -> None:
    """Stop unless audit6.py is the exact file audit 6 ran."""
    if a6.sha256_file(a6.__file__) != AUDIT6_SHA_LF:
        raise SystemExit("audit6.py is not the file audit 6 ran")
    if a6.SALT != SALT or a6.BAND != 4.0 or a6.SIDES != ("yes_base", "yes_label", "no_base"):
        raise SystemExit("audit6.py settings differ from the ones PLAN-7.md relies on")


def shard_pairs(pairs: list, shard: int) -> list:
    if len(pairs) != PAIRS_AVAILABLE:
        raise SystemExit("expected %d matched pairs, found %d" % (PAIRS_AVAILABLE, len(pairs)))
    start, end = SHARDS[shard]
    return pairs[start - 1:end]


def numbered(records: list, shard: int) -> list:
    start = SHARDS[shard][0]
    for i, r in enumerate(records):
        r["pair"] = start + i
    return records


def run_shard(llm, pairs: list, shard: int, budget_s: float, checkpoint=None,
              clock=time.monotonic) -> tuple[list, str]:
    """One shard's pairs in order, with audit 6's run loop; stops when the shard or the time budget runs out."""
    chosen = shard_pairs(pairs, shard)
    keep = (lambda recs: checkpoint(numbered(recs, shard))) if checkpoint else None
    records, stopped = a6.run_pairs(llm, chosen, MAX_TOKENS, budget_s, len(chosen), checkpoint=keep, clock=clock)
    return numbered(records, shard), stopped


def reply_tally(row: dict, long: bool) -> tuple[int, int]:
    """(changed, located) of one parsed reply if it is on the asked side of LONG_REPLY tokens, else (0, 0)."""
    if not row["parsed"] or (row["completion_tokens"] > LONG_REPLY) != long:
        return 0, 0
    return a6.tally(row)


def quantile(values: list, q: float):
    if not values:
        return None
    v = sorted(values)
    return v[min(len(v) - 1, int(q * len(v)))]


def descriptive(units: list, reps: int, seed: str) -> dict:
    """A comparison reported without a verdict."""
    out = a6.compare(units, 0, reps, seed, "direction")
    out.pop("verdict")
    out.pop("floor")
    return out


def analyse7(records: list[dict], reps: int = BOOT_REPS) -> dict:
    res: dict = {"pairs": len(records), "sides": {s: a6.side_summary([r[s] for r in records]) for s in a6.SIDES}}
    both = [r["same_excerpts"] for r in records if r["yes_base"]["parsed"] and r["yes_label"]["parsed"]]
    res["label_left_excerpts_identical"] = {"pairs_both_parsed": len(both), "identical": sum(both)}

    s1 = [a6.tally(r["yes_base"]) + a6.tally(r["no_base"]) for r in records]
    res["S1"] = dict(a6.compare(s1, FLOOR, reps, BOOT_SEED + "-S1", "direction"),
                     a_is="ELL essay, baseline prompt", b_is="matched non-ELL essay, baseline prompt")
    l1 = [a6.tally(r["yes_label"]) + a6.tally(r["yes_base"]) for r in records]
    res["L1"] = dict(a6.compare(l1, FLOOR, reps, BOOT_SEED + "-L1", "equivalence"), band_pts=a6.BAND,
                     a_is="ELL essay, ELL-label prompt", b_is="ELL essay, baseline prompt")
    t1 = []
    for r in records:
        lc = ll = sc = sl = 0
        for s in a6.SIDES:
            a, b = reply_tally(r[s], True)
            lc, ll = lc + a, ll + b
            a, b = reply_tally(r[s], False)
            sc, sl = sc + a, sl + b
        t1.append((lc, ll, sc, sl))
    res["T1"] = dict(a6.compare(t1, FLOOR_T1, reps, BOOT_SEED + "-T1", "direction"),
                     a_is="excerpts in replies of more than %d output tokens, all three calls" % LONG_REPLY,
                     b_is="excerpts in replies of at most %d output tokens, all three calls" % LONG_REPLY)

    # Reported without a prediction.
    full = [r for r in records if all(r[s]["parsed"] for s in a6.SIDES)]
    res["complete_pairs"] = {
        "pairs": len(full),
        "S1": descriptive([a6.tally(r["yes_base"]) + a6.tally(r["no_base"]) for r in full], reps,
                          BOOT_SEED + "-S1-complete"),
        "L1": descriptive([a6.tally(r["yes_label"]) + a6.tally(r["yes_base"]) for r in full], reps,
                          BOOT_SEED + "-L1-complete"),
    }
    res["pairs_with_a_cut_reply"] = sum(any(r[s]["finish_reason"] == "length" for s in a6.SIDES) for r in records)
    tokens: dict = {}
    lengths: dict = {}
    for s in a6.SIDES:
        done = [r[s]["completion_tokens"] for r in records if r[s]["finish_reason"] != "length"]
        tokens[s] = {"finished": len(done), "median": quantile(done, 0.5), "p90": quantile(done, 0.9),
                     "p95": quantile(done, 0.95), "max": max(done) if done else None,
                     "over_%d" % LONG_REPLY: sum(t > LONG_REPLY for t in done)}
        cells = {}
        for lo, hi in LENGTH_BANDS:
            changed, located = 0, 0
            for r in records:
                a, b = a6.tally(r[s], lo, hi)
                changed, located = changed + a, located + b
            cells["%d-%s" % (lo, hi if hi else "")] = {"located": located, "changed": changed}
        lengths[s] = cells
    res["reply_tokens"] = tokens
    res["excerpt_words"] = lengths
    by_score: dict = {}
    for r in records:
        cell = by_score.setdefault(r["score"], {"pairs": 0, **{s: [0, 0] for s in a6.SIDES}})
        cell["pairs"] += 1
        for s in a6.SIDES:
            a, b = a6.tally(r[s])
            cell[s][0] += a
            cell[s][1] += b
    res["by_score_changed_located"] = dict(sorted(by_score.items()))
    return res


def pool(reports: list[dict]) -> tuple[list, dict]:
    """Finished shard reports -> (records in pair order, per-shard counts), after checking they are one audit."""
    if not reports:
        raise SystemExit("no shard reports")
    same = ("audit7_sha256_lf", "audit6_sha256_lf", "plan_sha256_lf", "salt", "max_tokens", "threads")
    seen: dict = {}
    for rep in reports:
        if rep.get("audit") != AUDIT or rep.get("model", {}).get("name") != MODEL:
            raise SystemExit("not an audit-7 shard report")
        if rep.get("max_tokens") != MAX_TOKENS or rep.get("audit6_sha256_lf") != AUDIT6_SHA_LF:
            raise SystemExit("shard report used other settings than PLAN-7.md")
        for k in same:
            if rep.get(k) != reports[0].get(k):
                raise SystemExit("shard reports disagree on %s" % k)
        shard = rep.get("shard")
        if shard not in SHARDS or shard in seen:
            raise SystemExit("unknown or repeated shard %r" % shard)
        if not rep.get("complete"):
            raise SystemExit("shard %d did not finish" % shard)
        start = SHARDS[shard][0]
        if [r.get("pair") for r in rep["records"]] != list(range(start, start + len(rep["records"]))):
            raise SystemExit("shard %d records are not its pairs in order" % shard)
        seen[shard] = rep
    records = [r for k in sorted(seen) for r in seen[k]["records"]]
    shards = {str(k): {"pairs": len(v["records"]), "stopped": v["stopped"],
                       "first_pair": SHARDS[k][0], "last_pair_run": SHARDS[k][0] + len(v["records"]) - 1}
              for k, v in sorted(seen.items())}
    return records, shards


def run_main(args) -> int:
    check_audit6()
    with open(args.paths, encoding="utf-8") as fh:
        paths = json.load(fh)
    with open(args.models, encoding="utf-8") as fh:
        model = next(m for m in json.load(fh) if m["name"] == MODEL)
    pairs, unmatched, skipped = a6.make_pairs(a6.essays_from_csv(paths["persuade_csv"]))
    try:
        import llama_cpp
        version = getattr(llama_cpp, "__version__", "unknown")
    except ImportError:
        version = "not installed"
    here = os.path.dirname(os.path.abspath(__file__))
    start, end = SHARDS[args.shard]
    report = {"audit": AUDIT, "complete": False, "shard": args.shard, "first_pair": start, "last_pair": end,
              "plan_sha256_lf": a6.sha256_file(os.path.join(here, "PLAN-7.md")),
              "audit7_sha256_lf": a6.sha256_file(os.path.abspath(__file__)),
              "audit6_sha256_lf": a6.sha256_file(a6.__file__),
              "model": {k: model[k] for k in ("name", "repo", "commit", "file", "sha256", "license")},
              "salt": SALT, "pairs_available": len(pairs), "ell_essays_unmatched": unmatched,
              "probe_essays_left_out": skipped, "budget_minutes": args.budget_minutes,
              "system_prompt": a6.SYSTEM, "labels": a6.LABELS, "schema": a6.SCHEMA, "threads": args.threads,
              "n_ctx": args.ctx, "max_tokens": MAX_TOKENS, "llama_cpp_python": version,
              "python": sys.version.split()[0], "machine": platform.machine(), "os_cpu_count": os.cpu_count()}

    def write(records, stopped=None):
        report["stopped"] = stopped
        report["complete"] = stopped is not None
        report["analysis"] = analyse7(records, reps=1000)  # a quick look per shard; verdicts come from `pool`
        report["records"] = records
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)

    t0 = time.perf_counter()
    llm = a6.load_llm(paths["models"][MODEL], args.threads, args.ctx)
    report["load_seconds"] = round(time.perf_counter() - t0, 1)
    records, stopped = run_shard(llm, pairs, args.shard, args.budget_minutes * 60, checkpoint=write)
    write(records, stopped)
    print(json.dumps({"shard": args.shard, "pairs": len(records), "stopped": stopped}))
    return 0


def pool_main(args) -> int:
    reports = []
    for path in args.shard_json:
        with open(path, encoding="utf-8") as fh:
            reports.append(json.load(fh))
    records, shards = pool(reports)
    out = {"audit": AUDIT, "pooled_from": shards, "pairs": len(records),
           "audit7_sha256_lf": reports[0]["audit7_sha256_lf"], "plan_sha256_lf": reports[0]["plan_sha256_lf"],
           "pool_code_sha256_lf": a6.sha256_file(os.path.abspath(__file__)),
           "boot_reps": args.reps, "floors": {"S1": FLOOR, "L1": FLOOR, "T1": FLOOR_T1},
           "analysis": analyse7(records, reps=args.reps)}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    a = out["analysis"]
    print(json.dumps({"pairs": a["pairs"], **{k: {"diff_pts": a[k]["diff_pts"], "ci95": a[k]["ci95"],
                                                   "verdict": a[k]["verdict"]} for k in ("S1", "L1", "T1")}}))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="generate and classify one shard")
    r.add_argument("--shard", type=int, required=True, choices=sorted(SHARDS))
    r.add_argument("--paths", default="paths.json", help="written by fetch.py")
    r.add_argument("--models", default="models.json")
    r.add_argument("--budget-minutes", type=float, default=BUDGET_MINUTES)
    r.add_argument("--threads", type=int, default=2)
    r.add_argument("--ctx", type=int, default=4096)
    r.add_argument("--out", required=True)
    p = sub.add_parser("pool", help="join finished shard reports and judge S1, L1, T1")
    p.add_argument("--shard-json", nargs="+", required=True)
    p.add_argument("--reps", type=int, default=BOOT_REPS)
    p.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    return run_main(args) if args.cmd == "run" else pool_main(args)


if __name__ == "__main__":
    sys.exit(main())
