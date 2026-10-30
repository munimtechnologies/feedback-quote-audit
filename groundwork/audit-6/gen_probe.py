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
"""gen_probe: CPU speed and excerpt-format probe for audit 6, before any audit plan is written

Part of feedback-quote-audit groundwork, by MV2 of Munim, Inc. Made with AI agents working in his name.

Audit 6 asks whether telling a model that the student is an English language learner changes how
faithfully its feedback quotes the student. Before writing that plan we need to know how fast small
open models run on a shared CPU, whether they keep to an explicit excerpt-JSON format, and roughly
how many excerpts each call yields. This probe answers only that, on a few PERSUADE 2.0 essays
(Crossley et al. 2024, CC BY 4.0). Its numbers are for sizing the plan; they are not results.

Writes counts and timings only: no essay text, no feedback text, no essay ids.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import os
import platform
import re
import sys
import time

CSV_FIELD_LIMIT = 1 << 30
SALT = "audit6-speed-probe-2026-10-30"
MIN_WORDS, MAX_WORDS = 150, 700
GROUPS = ("Yes", "No")  # PERSUADE ell_status values

SCHEMA = {
    "type": "object",
    "properties": {
        "feedback": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"excerpt": {"type": "string"}, "comment": {"type": "string"}},
                "required": ["excerpt", "comment"],
            },
        },
    },
    "required": ["feedback"],
}

SYSTEM = ("You are an experienced writing teacher. Give the student feedback on their essay. "
          "Reply only with JSON of the form "
          '{"feedback": [{"excerpt": "...", "comment": "..."}]} '
          "with 3 to 5 items. Each excerpt must be copied exactly, word for word, from the essay.")
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
                             "assignment": (row.get("assignment") or "").strip()}
    return list(seen.values())


def rank(key: str) -> str:
    return hashlib.sha256((SALT + key).encode("utf-8")).hexdigest()


def pick(essays: list[dict], per_group: int) -> list[dict]:
    """per_group essays from each ELL group, in salted-hash order, within the word-count window."""
    out = []
    for group in GROUPS:
        pool = [e for e in essays if e["ell"] == group and MIN_WORDS <= len(e["text"].split()) <= MAX_WORDS]
        pool.sort(key=lambda e: rank(e["id"]))
        out.extend(pool[:per_group])
    return out


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


def run_model(llm, essays: list[dict], conditions: list[str], max_tokens: int) -> list[dict]:
    rows = []
    for k, essay in enumerate(essays):
        for cond in conditions:
            t0 = time.perf_counter()
            res = llm.create_chat_completion(messages=messages(essay, cond), temperature=0.0,
                                             max_tokens=max_tokens,
                                             response_format={"type": "json_object", "schema": SCHEMA})
            secs = time.perf_counter() - t0
            choice = res["choices"][0]
            usage = res.get("usage") or {}
            items = parse(choice["message"].get("content") or "")
            cats: dict = {}
            words = []
            for it in items or []:
                ex = it.get("excerpt") if isinstance(it.get("excerpt"), str) else ""
                c = classify(ex, essay["text"])
                cats[c] = cats.get(c, 0) + 1
                words.append(len(ex.split()))
            rows.append({"group": essay["ell"], "condition": cond, "seconds": round(secs, 2),
                         "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                         "completion_tokens": int(usage.get("completion_tokens") or 0),
                         "finish_reason": choice.get("finish_reason"), "parsed": items is not None,
                         "items": len(items or []), "categories": dict(sorted(cats.items())),
                         "excerpt_words": words})
            print("call %d/%d %s ell=%s %.1fs items=%d" % (len(rows), len(essays) * len(conditions), cond,
                                                         essay["ell"], secs, len(items or [])), flush=True)
    return rows


def summarise(rows: list[dict]) -> dict:
    cells: dict = {}
    for r in rows:
        for key in ("all", "%s|ell=%s" % (r["condition"], r["group"])):
            a = cells.setdefault(key, {"calls": 0, "parsed": 0, "truncated": 0, "items": 0, "seconds": 0.0,
                                       "prompt_tokens": 0, "completion_tokens": 0, "categories": {}})
            a["calls"] += 1
            a["parsed"] += int(r["parsed"])
            a["truncated"] += int(r["finish_reason"] == "length")
            a["items"] += r["items"]
            a["seconds"] += r["seconds"]
            a["prompt_tokens"] += r["prompt_tokens"]
            a["completion_tokens"] += r["completion_tokens"]
            for c, n in r["categories"].items():
                a["categories"][c] = a["categories"].get(c, 0) + n
    for a in cells.values():
        a["seconds"] = round(a["seconds"], 1)
        a["seconds_per_call"] = round(a["seconds"] / a["calls"], 1) if a["calls"] else 0.0
        a["items_per_call"] = round(a["items"] / a["calls"], 2) if a["calls"] else 0.0
        a["completion_tokens_per_second"] = (round(a["completion_tokens"] / a["seconds"], 2)
                                             if a["seconds"] else 0.0)
        a["categories"] = dict(sorted(a["categories"].items()))
    return dict(sorted(cells.items()))


def load_llm(path: str, threads: int, n_ctx: int):
    from llama_cpp import Llama  # imported here so the tests run without llama-cpp-python
    return Llama(model_path=path, n_ctx=n_ctx, n_threads=threads, n_threads_batch=threads, seed=0,
                 verbose=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--paths", default="paths.json", help="written by fetch.py")
    ap.add_argument("--models", default="models.json")
    ap.add_argument("--per-group", type=int, default=5)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--ctx", type=int, default=4096)
    ap.add_argument("--max-tokens", type=int, default=700)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    with open(args.paths, encoding="utf-8") as fh:
        paths = json.load(fh)
    with open(args.models, encoding="utf-8") as fh:
        models = json.load(fh)
    essays = pick(essays_from_csv(paths["persuade_csv"]), args.per_group)
    try:
        import llama_cpp
        version = getattr(llama_cpp, "__version__", "unknown")
    except ImportError:
        version = "not installed"
    report = {"probe": "audit-6 generation speed probe (sizing only, not results)",
              "essays": len(essays), "essays_by_ell_status": {g: sum(e["ell"] == g for e in essays) for g in GROUPS},
              "word_window": [MIN_WORDS, MAX_WORDS], "salt": SALT, "conditions": list(LABELS),
              "system_prompt": SYSTEM, "labels": LABELS, "threads": args.threads, "n_ctx": args.ctx,
              "max_tokens": args.max_tokens, "llama_cpp_python": version, "python": sys.version.split()[0],
              "machine": platform.machine(), "os_cpu_count": os.cpu_count(), "models": {}}
    for m in models:
        entry = {k: m[k] for k in ("repo", "commit", "file", "sha256", "license")}
        try:
            t0 = time.perf_counter()
            llm = load_llm(paths["models"][m["name"]], args.threads, args.ctx)
            entry["load_seconds"] = round(time.perf_counter() - t0, 1)
            rows = run_model(llm, essays, list(LABELS), args.max_tokens)
            entry["summary"] = summarise(rows)
            entry["calls"] = rows
            del llm
        except Exception as exc:  # noqa: BLE001 - record and go on to the next model
            entry["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:300])
        report["models"][m["name"]] = entry
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
    brief = {name: (e.get("error") or {k: e["summary"].get("all", {}).get(k) for k in
                                      ("calls", "parsed", "seconds_per_call", "items_per_call",
                                       "completion_tokens_per_second", "categories")})
             for name, e in report["models"].items()}
    print(json.dumps(brief))
    return 0


if __name__ == "__main__":
    sys.exit(main())
