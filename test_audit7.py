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
"""Tests for audit7 on synthetic data (no model, no network)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import audit6 as a6
import audit7 as a7

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


def essay(key: str, ell: str, score: str = "3") -> dict:
    return {"id": key, "ell": ell, "assignment": "Write.", "prompt": "P", "score": score, "text": ESSAY}


def row(tokens, *cats, words=10) -> dict:
    return {"seconds": 1.0, "prompt_tokens": 100, "completion_tokens": tokens, "finish_reason": "stop",
            "parsed": True, "items": len(cats), "excerpts": [[c, words] for c in cats]}


def cut() -> dict:
    return {"seconds": 1.0, "prompt_tokens": 100, "completion_tokens": a7.MAX_TOKENS, "finish_reason": "length",
            "parsed": False, "items": 0, "excerpts": []}


def record(score="3", **sides) -> dict:
    base = {"score": score, "yes_base": row(300, "exact", "exact", "changed_near"),
            "yes_label": row(300, "exact", "exact", "exact"),
            "no_base": row(500, "exact", "changed_near", "changed_loose"), "same_excerpts": False}
    base.update(sides)
    return base


def shard_report(shard, records, **over) -> dict:
    rep = {"audit": a7.AUDIT, "complete": True, "stopped": "budget", "shard": shard,
           "model": {"name": a7.MODEL}, "max_tokens": a7.MAX_TOKENS, "audit6_sha256_lf": a7.AUDIT6_SHA_LF,
           "audit7_sha256_lf": "x", "plan_sha256_lf": "y", "salt": a7.SALT, "threads": 2,
           "records": [dict(r, pair=a7.SHARDS[shard][0] + i) for i, r in enumerate(records)]}
    rep.update(over)
    return rep


class Settings(unittest.TestCase):
    def test_audit6_is_the_file_audit6_ran(self):
        a7.check_audit6()  # raises SystemExit otherwise
        self.assertEqual(a6.MAX_TOKENS, 450)
        self.assertEqual(a7.MAX_TOKENS, 800)

    def test_shards_are_disjoint_and_start_after_audit6(self):
        spans = [a7.SHARDS[k] for k in sorted(a7.SHARDS)]
        self.assertEqual(spans[0][0], 147)  # audit 6's Qwen run used pairs 1-146
        for (a, b), (c, d) in zip(spans, spans[1:]):
            self.assertEqual(c, b + 1)
        self.assertTrue(all(b - a + 1 == 160 for a, b in spans))
        self.assertLessEqual(spans[-1][1], a7.PAIRS_AVAILABLE)

    def test_wrong_pool_size_stops(self):
        with self.assertRaises(SystemExit):
            a7.shard_pairs([None] * 1000, 1)


class RunShard(unittest.TestCase):
    def setUp(self):
        y, n = essay("SECRET-Y", "Yes"), essay("SECRET-N", "No")
        self.pairs = [(y, n)] * a7.PAIRS_AVAILABLE
        self.pairs[306] = (essay("SECRET-Y307", "Yes", "5"), essay("SECRET-N307", "No", "5"))

    def test_takes_its_own_pairs_with_800_tokens_and_leaks_nothing(self):
        ticks = iter([0.0, 0.0, 0.0, 100.0])
        llm = FakeLlm([reply(620, "it helps them relax", "many students feel very stressed during the day"),
                       reply(300, "it helps them relax"),
                       reply(320, "a short break with friends online can help"),
                       reply(200, "it helps them relax"),
                       reply(210, "it helps them relax"),
                       ('{"feedback": [', "length", 800)])
        recs, stopped = a7.run_shard(llm, self.pairs, 2, 50.0, clock=lambda: next(ticks))
        self.assertEqual((len(recs), stopped), (2, "budget"))
        self.assertEqual([r["pair"] for r in recs], [307, 308])
        self.assertEqual([r["score"] for r in recs], ["5", "3"])  # pair 307 is index 306
        self.assertEqual([c["max_tokens"] for c in llm.calls], [800] * 6)
        self.assertIn("English language learner", llm.calls[1]["messages"][1]["content"])
        self.assertNotIn("English language learner", llm.calls[2]["messages"][1]["content"])
        self.assertEqual(llm.calls[0]["response_format"]["schema"], a6.SCHEMA)
        self.assertEqual(recs[0]["yes_base"]["completion_tokens"], 620)
        self.assertFalse(recs[1]["no_base"]["parsed"])
        dumped = json.dumps({"records": recs, "analysis": a7.analyse7(recs, reps=50)})
        for leak in ("SECRET", "relax", "stressed", "Note."):
            self.assertNotIn(leak, dumped)


class Analyse(unittest.TestCase):
    def test_under_the_floor_is_underpowered(self):
        res = a7.analyse7([record() for _ in range(9)] + [record(no_base=cut())], reps=50)
        for k in ("S1", "L1", "T1"):
            self.assertEqual(res[k]["verdict"], "underpowered")
        self.assertEqual(res["sides"]["no_base"]["truncated"], 1)
        self.assertEqual(res["pairs_with_a_cut_reply"], 1)
        self.assertEqual(res["complete_pairs"]["pairs"], 9)
        self.assertNotIn("verdict", res["complete_pairs"]["S1"])
        self.assertEqual(res["reply_tokens"]["no_base"]["finished"], 9)
        self.assertEqual(res["reply_tokens"]["no_base"]["over_450"], 9)
        self.assertEqual(res["excerpt_words"]["yes_base"]["7-10"], {"located": 30, "changed": 10})
        self.assertEqual(res["excerpt_words"]["yes_base"]["26-"], {"located": 0, "changed": 0})

    def test_verdicts_above_the_floor(self):
        res = a7.analyse7([record() for _ in range(250)], reps=50)
        # yes_base 1/3 changed, yes_label 0/3, no_base 2/3 (a reply of 500 tokens, so "long")
        self.assertEqual(res["S1"]["a"]["located"], 750)
        self.assertEqual(res["S1"]["diff_pts"], -33.33)
        self.assertEqual(res["S1"]["verdict"], "reversed")
        self.assertEqual(res["L1"]["diff_pts"], -33.33)
        self.assertEqual(res["L1"]["verdict"], "did not hold")
        self.assertEqual((res["T1"]["a"]["changed"], res["T1"]["a"]["located"]), (500, 750))
        self.assertEqual((res["T1"]["b"]["changed"], res["T1"]["b"]["located"]), (250, 1500))
        self.assertEqual(res["T1"]["diff_pts"], 50.0)
        self.assertEqual(res["T1"]["verdict"], "held")
        self.assertEqual(res["T1"]["floor"], 150)

    def test_equivalence_holds_when_label_changes_nothing(self):
        same = row(300, "exact", "exact", "changed_near")
        res = a7.analyse7([record(yes_label=same) for _ in range(250)], reps=50)
        self.assertEqual(res["L1"]["diff_pts"], 0.0)
        self.assertEqual(res["L1"]["verdict"], "held")

    def test_reply_tally_splits_at_450(self):
        self.assertEqual(a7.reply_tally(row(450, "changed_near"), True), (0, 0))
        self.assertEqual(a7.reply_tally(row(450, "changed_near"), False), (1, 1))
        self.assertEqual(a7.reply_tally(row(451, "exact"), True), (0, 1))
        self.assertEqual(a7.reply_tally(cut(), False), (0, 0))


class Pool(unittest.TestCase):
    def test_pools_in_shard_order(self):
        recs, shards = a7.pool([shard_report(3, [record("4")]), shard_report(1, [record("2"), record("3")])])
        self.assertEqual([r["pair"] for r in recs], [147, 148, 467])
        self.assertEqual(shards["1"]["last_pair_run"], 148)
        self.assertEqual(sorted(shards), ["1", "3"])

    def test_refuses_mixed_or_unfinished_shards(self):
        good = shard_report(1, [record()])
        for bad in (shard_report(2, [record()], audit7_sha256_lf="other"),
                    shard_report(2, [record()], max_tokens=450),
                    shard_report(2, [record()], complete=False),
                    shard_report(1, [record()]),
                    dict(shard_report(2, [record()]), shard=9),
                    dict(shard_report(2, [record()]), records=[dict(record(), pair=400)])):
            with self.assertRaises(SystemExit):
                a7.pool([good, bad])
        with self.assertRaises(SystemExit):
            a7.pool([])

    def test_pool_command_writes_verdicts(self):
        with tempfile.TemporaryDirectory() as d:
            paths = []
            for shard in (1, 2):
                p = os.path.join(d, "s%d.json" % shard)
                with open(p, "w", encoding="utf-8") as fh:
                    json.dump(shard_report(shard, [record() for _ in range(130)]), fh)
                paths.append(p)
            out = os.path.join(d, "pooled.json")
            self.assertEqual(a7.main(["pool", "--shard-json", *paths, "--reps", "50", "--out", out]), 0)
            with open(out, encoding="utf-8") as fh:
                pooled = json.load(fh)
        self.assertEqual(pooled["pairs"], 260)
        self.assertEqual(pooled["analysis"]["S1"]["verdict"], "reversed")
        self.assertEqual(pooled["floors"], {"S1": 600, "L1": 600, "T1": 150})


if __name__ == "__main__":
    unittest.main()
