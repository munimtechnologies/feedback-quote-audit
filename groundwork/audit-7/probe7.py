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
"""probe7: how many tokens audit 6's prompt really needs, re-run on pairs audit 6 already used

Groundwork for feedback-quote-audit audit 7, by MV2 of Munim, Inc. Made with AI agents working in his name.
A sizing probe, not results. It re-runs the first pairs of audit 6 with the same code (audit6.py), prompt,
model, seed and threads, changing only the token limit, and compares each call with audit 6's own record of it
in audit6-qwen.json. No new essays are spent, so audit 7 can still use every pair audit 6 did not reach.

Writes counts only: no essay text, no feedback text, no essay ids.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import audit6 as a6

CAPS = (450, 550, 600, 700, 800, 900, 1024)
TARGET_CUT = 0.05  # the token limit audit 7 needs should cut at most this share of replies
JOB_MINUTES = 480


def cut_at(row: dict, cap: int, max_tokens: int) -> bool:
    """Would this reply have been cut off with a limit of cap tokens?"""
    if row["finish_reason"] == "length" and row["completion_tokens"] >= max_tokens:
        return True  # cut even at this probe's own limit
    return row["completion_tokens"] > cap


def compare_call(old: dict, new: dict) -> dict:
    """One call: audit 6's record against the probe's re-run of it (counts only)."""
    both = old["parsed"] and new["parsed"]
    return {"old_finish": old["finish_reason"], "old_tokens": old["completion_tokens"],
            "old_parsed": old["parsed"], "new_finish": new["finish_reason"],
            "new_tokens": new["completion_tokens"], "new_parsed": new["parsed"], "seconds": new["seconds"],
            "new_items": new["items"], "new_excerpts": new["excerpts"],
            "same_categories": (old["excerpts"] == new["excerpts"]) if both else None}


def quantile(values: list, q: float):
    if not values:
        return None
    v = sorted(values)
    return v[min(len(v) - 1, int(q * len(v)))]


def located_changed(excerpts: list) -> tuple[int, int]:
    located = sum(c in a6.LOCATED for c, _ in excerpts)
    changed = sum(c in a6.CHANGED for c, _ in excerpts)
    return located, changed


def summarise(pairs: list[dict], max_tokens: int) -> dict:
    """pairs: [{side: compare_call(...)}] in run order."""
    calls = [p[s] for p in pairs for s in a6.SIDES]
    n = len(calls)
    as_rows = [{"finish_reason": c["new_finish"], "completion_tokens": c["new_tokens"]} for c in calls]
    cut = {str(cap): sum(cut_at(r, cap, max_tokens) for r in as_rows) for cap in CAPS if cap <= max_tokens}
    pick = next((int(cap) for cap, k in cut.items() if n and k <= TARGET_CUT * n), None)
    finished = [c["new_tokens"] for c in calls if c["new_finish"] != "length"]
    both = [c for c in calls if c["same_categories"] is not None]
    old_cut = [c for c in calls if c["old_finish"] == "length"]
    rescued = [c for c in old_cut if c["new_parsed"]]
    kept = [c for c in calls if c["old_parsed"] and c["new_parsed"]]
    r_loc, r_chg = map(sum, zip(*[located_changed(c["new_excerpts"]) for c in rescued])) if rescued else (0, 0)
    k_loc, k_chg = map(sum, zip(*[located_changed(c["new_excerpts"]) for c in kept])) if kept else (0, 0)
    pair_secs = [sum(p[s]["seconds"] for s in a6.SIDES) for p in pairs]
    mean_pair = sum(pair_secs) / len(pair_secs) if pair_secs else None
    by_side = {}
    for s in a6.SIDES:
        rows = [p[s] for p in pairs]
        loc = sum(located_changed(r["new_excerpts"])[0] for r in rows)
        by_side[s] = {"calls": len(rows), "old_cut_450": sum(r["old_finish"] == "length" for r in rows),
                      "new_cut": sum(r["new_finish"] == "length" for r in rows),
                      "new_parsed": sum(r["new_parsed"] for r in rows), "located": loc,
                      "located_per_call": round(loc / len(rows), 2) if rows else None}
    return {
        "pairs": len(pairs), "calls": n, "max_tokens": max_tokens,
        "cut_if_limit_were": cut, "target_cut_share": TARGET_CUT, "smallest_limit_meeting_target": pick,
        "finished_tokens": {"median": quantile(finished, 0.5), "p90": quantile(finished, 0.9),
                            "p95": quantile(finished, 0.95), "max": max(finished) if finished else None},
        "by_side": by_side,
        "determinism": {"calls_parsed_both_times": len(both),
                        "same_categories": sum(c["same_categories"] for c in both),
                        "finished_both_times_same_tokens": sum(
                            c["old_finish"] != "length" and c["new_finish"] != "length"
                            and c["old_tokens"] == c["new_tokens"] for c in calls),
                        "finished_both_times": sum(c["old_finish"] != "length" and c["new_finish"] != "length"
                                                   for c in calls)},
        "cut_in_audit6": {"calls": len(old_cut), "now_parsed": len(rescued), "located": r_loc, "changed": r_chg,
                          "changed_pct": a6.pct(r_chg, r_loc)},
        "parsed_in_both": {"calls": len(kept), "located": k_loc, "changed": k_chg,
                           "changed_pct": a6.pct(k_chg, k_loc)},
        "seconds": {"mean_call": round(sum(c["seconds"] for c in calls) / n, 1) if n else None,
                    "median_call": quantile([c["seconds"] for c in calls], 0.5),
                    "max_call": max((c["seconds"] for c in calls), default=None),
                    "mean_pair": round(mean_pair, 1) if mean_pair else None,
                    "pairs_per_480_min_job": int(JOB_MINUTES * 60 // mean_pair) if mean_pair else None},
    }


def check_old(old: dict) -> list:
    """audit 6's Qwen report, checked to be the run this probe re-runs."""
    if old.get("salt") != a6.SALT or old.get("model", {}).get("name") != "qwen2.5-1.5b-instruct-q4_k_m":
        raise SystemExit("audit6-qwen.json is not audit 6's Qwen run")
    if old.get("max_tokens") != a6.MAX_TOKENS or old.get("system_prompt") != a6.SYSTEM:
        raise SystemExit("audit6-qwen.json used other settings than audit6.py")
    return old["records"]


def run(llm, pairs: list, old_records: list, n: int, max_tokens: int, budget_s: float,
        checkpoint=None, clock=time.monotonic) -> tuple[list, str]:
    t0 = clock()
    out: list = []
    stopped = "count"
    for i in range(min(n, len(old_records), len(pairs))):
        if clock() - t0 >= budget_s:
            stopped = "budget"
            break
        y, no = pairs[i]
        if y["score"] != old_records[i]["score"]:
            raise SystemExit("pair %d does not line up with audit 6's record" % (i + 1))
        rec = {}
        for side, essay, cond in (("yes_base", y, "baseline"), ("yes_label", y, "ell"), ("no_base", no, "baseline")):
            new, _ = a6.call(llm, essay, cond, max_tokens)
            rec[side] = compare_call(old_records[i][side], new)
        out.append(rec)
        print("pair %d: tokens %s (audit 6: %s)" % (
            i + 1, "/".join(str(rec[s]["new_tokens"]) for s in a6.SIDES),
            "/".join(str(rec[s]["old_tokens"]) for s in a6.SIDES)), flush=True)
        if checkpoint:
            checkpoint(out)
    return out, stopped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--paths", default="paths.json")
    ap.add_argument("--models", default="models.json")
    ap.add_argument("--audit6-json", default="audit6-qwen.json")
    ap.add_argument("--pairs", type=int, default=20)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--ctx", type=int, default=4096)
    ap.add_argument("--budget-minutes", type=float, default=240)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    with open(args.paths, encoding="utf-8") as fh:
        paths = json.load(fh)
    with open(args.models, encoding="utf-8") as fh:
        model = next(m for m in json.load(fh) if m["name"] == "qwen2.5-1.5b-instruct-q4_k_m")
    with open(args.audit6_json, encoding="utf-8") as fh:
        old_records = check_old(json.load(fh))
    pairs, _, _ = a6.make_pairs(a6.essays_from_csv(paths["persuade_csv"]))
    report = {"probe": "feedback-quote-audit groundwork/audit-7 probe7 (sizing, not results)",
              "audit6_sha256_lf": a6.sha256_file(a6.__file__), "model": model["name"],
              "threads": args.threads, "n_ctx": args.ctx, "max_tokens": args.max_tokens,
              "budget_minutes": args.budget_minutes, "pairs_asked": args.pairs}

    def write(recs, stopped=None):
        report["stopped"] = stopped
        report["summary"] = summarise(recs, args.max_tokens)
        report["pairs"] = recs
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)

    llm = a6.load_llm(paths["models"][model["name"]], args.threads, args.ctx)
    recs, stopped = run(llm, pairs, old_records, args.pairs, args.max_tokens, args.budget_minutes * 60,
                        checkpoint=write)
    write(recs, stopped)
    s = report["summary"]
    print(json.dumps({k: s[k] for k in ("pairs", "cut_if_limit_were", "smallest_limit_meeting_target",
                                        "finished_tokens", "determinism", "cut_in_audit6", "seconds")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
