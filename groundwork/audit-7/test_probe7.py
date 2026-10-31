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
"""Tests for probe7 on synthetic data (no model, no network)."""
from __future__ import annotations

import json
import unittest

import audit6 as a6
import probe7 as p7

ESSAY = ("Students should be allowed to use phones at lunch because it helps them relax. "
         "Many students feel stressed during the day, and a short break with friends online can help.")


class FakeLlm:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def create_chat_completion(self, **kw):
        self.calls.append(kw)
        content, finish, tokens = self.replies.pop(0)
        return {"choices": [{"message": {"content": content}, "finish_reason": finish}],
                "usage": {"prompt_tokens": 100, "completion_tokens": tokens}}


def reply(tokens, *excerpts) -> tuple:
    return json.dumps({"feedback": [{"excerpt": e, "comment": "Note."} for e in excerpts]}), "stop", tokens


def old_row(finish, tokens, *cats_words) -> dict:
    return {"seconds": 1.0, "prompt_tokens": 1, "completion_tokens": tokens, "finish_reason": finish,
            "parsed": finish == "stop", "items": len(cats_words), "excerpts": [list(c) for c in cats_words]}


def essay(key: str, ell: str, score: str = "3") -> dict:
    return {"id": key, "ell": ell, "assignment": "Write.", "prompt": "P", "score": score, "text": ESSAY}


class Cut(unittest.TestCase):
    def test_cut_at(self):
        self.assertTrue(p7.cut_at({"finish_reason": "stop", "completion_tokens": 500}, 450, 1024))
        self.assertFalse(p7.cut_at({"finish_reason": "stop", "completion_tokens": 450}, 450, 1024))
        self.assertTrue(p7.cut_at({"finish_reason": "length", "completion_tokens": 1024}, 1024, 1024))


class RunAndSummarise(unittest.TestCase):
    def setUp(self):
        self.pairs = [(essay("SECRET-Y1", "Yes", "2"), essay("SECRET-N1", "No", "2")),
                      (essay("SECRET-Y2", "Yes", "4"), essay("SECRET-N2", "No", "4"))]
        self.old = [
            {"score": "2", "yes_base": old_row("length", 450), "yes_label": old_row("stop", 300, ("exact", 4)),
             "no_base": old_row("stop", 320, ("exact", 4))},
            {"score": "4", "yes_base": old_row("stop", 200, ("exact", 4)),
             "yes_label": old_row("length", 450), "no_base": old_row("length", 450)},
        ]

    def test_run_compares_with_audit6_and_leaks_nothing(self):
        llm = FakeLlm([reply(600, "it helps them relax", "many students feel very stressed during the day"),
                       reply(300, "it helps them relax"),
                       reply(320, "it helps them relax"),
                       reply(200, "it helps them relax"),
                       reply(520, "a short break with friends online can help"),
                       ('{"feedback": [', "length", 1024)])
        recs, stopped = p7.run(llm, self.pairs, self.old, 5, 1024, 1e9)
        self.assertEqual((len(recs), stopped), (2, "count"))
        self.assertEqual([c["max_tokens"] for c in llm.calls], [1024] * 6)
        self.assertIn("English language learner", llm.calls[1]["messages"][1]["content"])
        self.assertEqual(llm.calls[0]["response_format"]["schema"], a6.SCHEMA)
        first = recs[0]
        self.assertEqual((first["yes_base"]["old_finish"], first["yes_base"]["new_tokens"]), ("length", 600))
        self.assertIsNone(first["yes_base"]["same_categories"])
        self.assertTrue(first["yes_label"]["same_categories"])
        s = p7.summarise(recs, 1024)
        self.assertEqual(s["calls"], 6)
        self.assertEqual(s["cut_if_limit_were"]["450"], 3)  # 600, 520 and the one cut at 1024
        self.assertEqual(s["cut_if_limit_were"]["700"], 1)
        self.assertEqual(s["cut_if_limit_were"]["1024"], 1)
        self.assertIsNone(s["smallest_limit_meeting_target"])  # 1 of 6 is over 5%
        self.assertEqual(s["cut_in_audit6"]["calls"], 3)
        self.assertEqual(s["cut_in_audit6"]["now_parsed"], 2)
        self.assertEqual((s["cut_in_audit6"]["located"], s["cut_in_audit6"]["changed"]), (3, 1))
        self.assertEqual(s["determinism"]["calls_parsed_both_times"], 3)
        self.assertEqual(s["determinism"]["same_categories"], 3)
        self.assertEqual(s["determinism"]["finished_both_times_same_tokens"], 3)
        self.assertEqual(s["by_side"]["no_base"]["new_cut"], 1)
        self.assertEqual(s["finished_tokens"]["max"], 600)
        dumped = json.dumps({"pairs": recs, "summary": s})
        for leak in ("SECRET", "relax", "stressed", "Note."):
            self.assertNotIn(leak, dumped)

    def test_target_met_when_few_are_cut(self):
        call = {"old_finish": "stop", "old_tokens": 300, "old_parsed": True, "new_finish": "stop",
                "new_tokens": 300, "new_parsed": True, "seconds": 10.0, "new_items": 1,
                "new_excerpts": [["exact", 4]], "same_categories": True}
        long = dict(call, new_tokens=650)
        pairs = [{s: call for s in a6.SIDES} for _ in range(10)]
        pairs[0] = dict(pairs[0], yes_base=long)
        s = p7.summarise(pairs, 1024)
        self.assertEqual(s["smallest_limit_meeting_target"], 450)  # 1 of 30 is 3.3%
        self.assertEqual(s["seconds"]["pairs_per_480_min_job"], 960)

    def test_misaligned_pairs_stop(self):
        old = [dict(self.old[0], score="5")]
        with self.assertRaises(SystemExit):
            p7.run(FakeLlm([]), self.pairs, old, 1, 1024, 1e9)

    def test_budget(self):
        ticks = iter([0.0, 0.0, 100.0])
        llm = FakeLlm([reply(10, "it helps them relax")] * 3)
        recs, stopped = p7.run(llm, self.pairs, self.old, 5, 1024, 50.0, clock=lambda: next(ticks))
        self.assertEqual((len(recs), stopped), (1, "budget"))

    def test_check_old(self):
        good = {"salt": a6.SALT, "model": {"name": "qwen2.5-1.5b-instruct-q4_k_m"}, "max_tokens": a6.MAX_TOKENS,
                "system_prompt": a6.SYSTEM, "records": self.old}
        self.assertEqual(p7.check_old(good), self.old)
        with self.assertRaises(SystemExit):
            p7.check_old(dict(good, salt="other"))
        with self.assertRaises(SystemExit):
            p7.check_old(dict(good, max_tokens=700))


if __name__ == "__main__":
    unittest.main()
