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
"""Tests for audit6 on synthetic data (no model, no network)."""
from __future__ import annotations

import csv
import json
import os
import tempfile
import unittest

import audit6 as a6

ESSAY = ("Students should be allowed to use phones at lunch because it helps them relax. "
         "Many students feel stressed during the day, and a short break with friends online can help. "
         "However, phones must stay off in class so that everyone can focus on learning.")


def essay(i: int, ell: str, prompt: str = "Phones", score: str = "3", words: int = 200) -> dict:
    return {"id": "E%03d" % i, "ell": ell, "assignment": "Write about phones.", "prompt": prompt,
            "score": score, "text": " ".join(["word%d" % i] * words)}


class FakeLlm:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def create_chat_completion(self, **kw):
        self.calls.append(kw)
        content, finish = self.replies.pop(0)
        return {"choices": [{"message": {"content": content}, "finish_reason": finish}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50}}


def reply(*excerpts) -> tuple:
    return json.dumps({"feedback": [{"excerpt": e, "comment": "Note."} for e in excerpts]}), "stop"


def row(*cats_words) -> dict:
    return {"seconds": 1.0, "prompt_tokens": 1, "completion_tokens": 1, "finish_reason": "stop",
            "parsed": True, "items": len(cats_words), "excerpts": [list(c) for c in cats_words]}


class Classify(unittest.TestCase):
    def test_categories(self):
        self.assertEqual(a6.classify("it helps them relax", ESSAY), "exact")
        self.assertEqual(a6.classify(chr(0x201C) + "Many  students feel STRESSED during the day." + chr(0x201D), ESSAY),
                         "format_only")
        self.assertEqual(a6.classify("Many students feel stressed ... phones must stay off in class", ESSAY),
                         "ellipsis_join")
        self.assertEqual(a6.classify("many students feel very stressed during the day and a short break", ESSAY),
                         "changed_near")
        self.assertEqual(a6.classify("phones should stay off in every class so students focus", ESSAY),
                         "changed_loose")
        self.assertEqual(a6.classify("the electoral college should be abolished now", ESSAY), "not_found")
        self.assertEqual(a6.classify("   ", ESSAY), "empty")

    def test_spelling_fix_counts_as_changed(self):
        text = "Many studens feel stressed during the day and need a short break."
        self.assertEqual(a6.classify("Many students feel stressed during the day", text), "changed_near")

    def test_excerpt_words(self):
        self.assertEqual(a6.excerpt_words(chr(0x201C) + "It's a  short, clear one." + chr(0x201D)), 5)
        self.assertEqual(a6.excerpt_words("..."), 0)


class Parse(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(a6.parse('{"feedback": [{"excerpt": "a", "comment": "b"}, 3]}'),
                         [{"excerpt": "a", "comment": "b"}])
        self.assertIsNone(a6.parse('{"feedback": [{"excerpt": "a"'))
        self.assertIsNone(a6.parse('["x"]'))

    def test_schema_asks_for_three_items(self):
        arr = a6.SCHEMA["properties"]["feedback"]
        self.assertEqual((arr["minItems"], arr["maxItems"]), (3, 3))
        self.assertNotIn("maxLength", arr["items"]["properties"]["excerpt"])


class Select(unittest.TestCase):
    def test_csv_fields(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "train.csv")
            with open(path, "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["essay_id_comp", "full_text", "ell_status", "assignment", "prompt_name",
                            "holistic_essay_score"])
                w.writerow(["A1", ESSAY, "Yes ", "Write.", "Phones", "3"])
                w.writerow(["A1", ESSAY, "Yes ", "Write.", "Phones", "3"])
                w.writerow(["B2", ESSAY, "No", "Write.", "Venus", "4"])
            got = a6.essays_from_csv(path)
        self.assertEqual([(e["id"], e["ell"], e["prompt"], e["score"]) for e in got],
                         [("A1", "Yes", "Phones", "3"), ("B2", "No", "Venus", "4")])

    def test_pairs_matched_deterministic_and_probe_left_out(self):
        pool = [essay(i, "Yes", score=str(1 + i % 2)) for i in range(20)]
        pool += [essay(i, "No", score=str(1 + i % 2)) for i in range(20, 50)]
        pool.append(essay(90, "Yes", score="6"))  # no non-ELL essay with score 6
        pool.append(essay(91, "Yes", words=50))  # too short
        pool.append(essay(92, "", score="1"))  # blank status
        pairs, unmatched, skipped = a6.make_pairs(pool)
        again, _, _ = a6.make_pairs(list(reversed(pool)))
        self.assertEqual([(y["id"], n["id"]) for y, n in pairs], [(y["id"], n["id"]) for y, n in again])
        self.assertEqual(skipped, 10)
        probe = a6.probe_ids(pool)
        used = [e["id"] for p in pairs for e in p]
        self.assertFalse(probe & set(used))
        self.assertEqual(len(used), len(set(used)))
        for y, n in pairs:
            self.assertEqual((y["ell"], n["ell"]), ("Yes", "No"))
            self.assertEqual((y["prompt"], y["score"]), (n["prompt"], n["score"]))
        self.assertNotIn("E091", used)
        self.assertNotIn("E092", used)
        # 21 in-window ELL essays less 5 probe essays; E090 (score 6) is unmatched unless the probe took it
        self.assertEqual(unmatched, 0 if "E090" in probe else 1)
        self.assertEqual(len(pairs) + unmatched, 16)

    def test_messages_label(self):
        e = essay(1, "Yes")
        base = a6.messages(e, "baseline")[1]["content"]
        ell = a6.messages(e, "ell")[1]["content"]
        self.assertTrue(ell.endswith(base))
        self.assertIn("English language learner", ell)
        self.assertNotIn("English language learner", base)


class Run(unittest.TestCase):
    def test_three_calls_per_pair_in_order(self):
        y = {"id": "SECRET-Y", "ell": "Yes", "assignment": "Write.", "prompt": "P", "score": "2", "text": ESSAY}
        n = {"id": "SECRET-N", "ell": "No", "assignment": "Write.", "prompt": "P", "score": "2", "text": ESSAY}
        same = reply("it helps them relax", "the electoral college")
        llm = FakeLlm([same, same, ('{"feedback": [', "length")])
        records, stopped = a6.run_pairs(llm, [(y, n)], 450, 3600, 10)
        self.assertEqual(stopped, "pool")
        self.assertEqual(len(llm.calls), 3)
        self.assertNotIn("English language learner", llm.calls[0]["messages"][1]["content"])
        self.assertIn("English language learner", llm.calls[1]["messages"][1]["content"])
        self.assertNotIn("English language learner", llm.calls[2]["messages"][1]["content"])
        self.assertEqual(llm.calls[0]["response_format"]["schema"], a6.SCHEMA)
        r = records[0]
        self.assertEqual(r["yes_base"]["excerpts"], [["exact", 4], ["not_found", 3]])
        self.assertTrue(r["same_excerpts"])
        self.assertFalse(r["no_base"]["parsed"])
        dumped = json.dumps({"records": records, "analysis": a6.analyse(records, reps=50)})
        for leak in ("SECRET", "relax", "electoral", "Note."):
            self.assertNotIn(leak, dumped)

    def test_stops_on_budget_and_max_pairs(self):
        pairs = [(essay(1, "Yes"), essay(2, "No"))] * 3
        ticks = iter([0.0, 0.0, 100.0])
        llm = FakeLlm([reply("word1 word1 word1")] * 9)
        records, stopped = a6.run_pairs(llm, pairs, 450, 50.0, 10, clock=lambda: next(ticks))
        self.assertEqual((len(records), stopped), (1, "budget"))
        llm = FakeLlm([reply("word1 word1 word1")] * 9)
        records, stopped = a6.run_pairs(llm, pairs, 450, 1e9, 2)
        self.assertEqual((len(records), stopped), (2, "max_pairs"))
        self.assertTrue(records[0]["same_excerpts"])


class Analyse(unittest.TestCase):
    def test_tally(self):
        r = row(("exact", 5), ("changed_near", 5), ("changed_loose", 12), ("not_found", 5), ("empty", 0))
        self.assertEqual(a6.tally(r), (2, 3))
        self.assertEqual(a6.tally(r, 4, 6), (1, 2))
        self.assertEqual(a6.tally(r, 11), (1, 1))

    def test_verdicts(self):
        self.assertEqual(a6.direction_verdict(0.5, 3.0), "held")
        self.assertEqual(a6.direction_verdict(-3.0, -0.5), "reversed")
        self.assertEqual(a6.direction_verdict(-1.0, 1.0), "no clear difference")
        self.assertEqual(a6.equivalence_verdict(-3.9, 3.9), "held")
        self.assertEqual(a6.equivalence_verdict(4.1, 9.0), "did not hold")
        self.assertEqual(a6.equivalence_verdict(-9.0, -4.1), "did not hold")
        self.assertEqual(a6.equivalence_verdict(-1.0, 5.0), "inconclusive")

    def test_boot_diff_deterministic(self):
        units = [(1, 2, 0, 2), (0, 2, 1, 2), (2, 2, 0, 2)]
        self.assertEqual(a6.boot_diff(units, 200, "s"), a6.boot_diff(units, 200, "s"))
        lo, hi, k = a6.boot_diff(units, 200, "s")
        self.assertTrue(lo <= 100.0 * (3 / 6 - 1 / 6) <= hi)
        self.assertEqual(a6.boot_diff([], 200, "s"), (None, None, 0))

    def test_analyse_powered_and_underpowered(self):
        records = []
        for i in range(160):
            ell_changed = ("changed_near", 5) if i % 2 == 0 else ("exact", 5)
            records.append({"score": str(1 + i % 3),
                            "yes_base": row(ell_changed, ("exact", 12)),
                            "yes_label": row(ell_changed, ("exact", 12)),
                            "no_base": row(("exact", 5), ("exact", 12)),
                            "same_excerpts": True})
        res = a6.analyse(records, reps=300)
        self.assertEqual(res["S1"]["a"], {"changed": 80, "located": 320, "rate_pct": 25.0})
        self.assertEqual(res["S1"]["b"]["rate_pct"], 0.0)
        self.assertEqual(res["S1"]["verdict"], "held")
        self.assertEqual(res["L1"]["diff_pts"], 0.0)
        self.assertEqual(res["L1"]["verdict"], "held")
        self.assertEqual(res["C1"]["a"]["located"], 480)
        self.assertEqual(res["C1"]["b"]["changed"], 0)
        self.assertEqual(res["C1"]["verdict"], "held")
        self.assertEqual(res["label_left_excerpts_identical"], {"pairs_both_parsed": 160, "identical": 160})
        self.assertEqual(sorted(res["by_score_changed_located"]), ["1", "2", "3"])
        self.assertEqual(res["sides"]["yes_base"]["changed_pct"], 25.0)
        small = a6.analyse(records[:10], reps=50)
        self.assertEqual(small["S1"]["verdict"], "underpowered")
        self.assertEqual(small["L1"]["verdict"], "underpowered")
        self.assertEqual(a6.analyse([], reps=50)["S1"]["verdict"], "underpowered")


if __name__ == "__main__":
    unittest.main()
