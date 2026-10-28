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
"""Tests for length_tight.py. Every text here is made up; no dataset text is used."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import length_tight as lt

QUESTION = "Describe a time you learned something new. Give details and examples."
ESSAY = ("The quick brown fox jumps over the lazy dog near the river bank every morning. "
         "My family went to the beach last summer for a week. "
         "It was the best day of the whole year.\n\n"
         "In conclusion, I learned a lot from this trip.")
# 1: 6-word exact substring -> primary, bin 4-6 (0), tight, not changed.
# 2: 12-word span with fox->cat -> primary, bin 11-15 (2), tight, word_changed.
# 3: under 4 words -> excluded. 4: exact but rewrite-cued -> excluded.
QUOTES = ['You wrote "My family went to the beach".',
          'You wrote "The quick brown cat jumps over the lazy dog near the river".',
          'You wrote "the lazy dog".',
          'Instead, you could write "It was the best day of the whole year".']
ROW = {"idx": 0, "band": "5.0", "human": QUESTION + "\n\n" + ESSAY,
       "evaluation": "\n".join(QUOTES), "reasoning": ""}
ROW2 = {**ROW, "idx": 1}

# Per-bin arrays expected from length_row(ROW): only bins 0 (4-6) and 2 (11-15) are populated.
WANT = {"n": [1, 0, 1, 0, 0], "prim_tight": [1, 0, 1, 0, 0], "wc": [0, 0, 1, 0, 0],
        "wc_tight": [0, 0, 1, 0, 0], "wc_loose": [0, 0, 0, 0, 0]}


class CountsTests(unittest.TestCase):
    def test_exact_tight(self):
        self.assertEqual(lt.counts(1.0, "exact"),
                         {"n": 1, "prim_tight": 1, "wc": 0, "wc_tight": 0, "wc_loose": 0})

    def test_changed_tight(self):
        self.assertEqual(lt.counts(0.9, "word_changed"),
                         {"n": 1, "prim_tight": 1, "wc": 1, "wc_tight": 1, "wc_loose": 0})

    def test_changed_loose(self):
        self.assertEqual(lt.counts(0.7, "word_changed"),
                         {"n": 1, "prim_tight": 0, "wc": 1, "wc_tight": 0, "wc_loose": 1})

    def test_tight_boundary_is_tight(self):
        c = lt.counts(lt.TIGHT, "word_changed")  # exactly 0.8 counts as tight
        self.assertEqual((c["wc_tight"], c["wc_loose"]), (1, 0))

    def test_changed_only_for_word_changed(self):
        c = lt.counts(0.7, "elision_words")
        self.assertEqual((c["n"], c["prim_tight"], c["wc"], c["wc_loose"]), (1, 0, 0, 0))


class BinTests(unittest.TestCase):
    def test_bin_of(self):
        self.assertEqual([lt.bin_of(n) for n in (4, 6, 7, 10, 11, 15, 16, 25, 26, 500)],
                         [0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
        self.assertIsNone(lt.bin_of(3))


class RowTests(unittest.TestCase):
    def test_length_row(self):
        out = lt.length_row(ROW)
        for key in lt.KEYS:
            self.assertEqual(out[key], WANT[key], key)
        # the one changed quote is tight, so wc_tight + wc_loose == wc in every bin
        for b in range(len(lt.BINS)):
            self.assertEqual(out["wc_tight"][b] + out["wc_loose"][b], out["wc"][b])


class VerdictTests(unittest.TestCase):
    def test_verdict_dir(self):
        self.assertEqual(lt.verdict_dir((0.01, 0.03), 500, 500, 100, +1), "held (long quotes higher)")
        self.assertEqual(lt.verdict_dir((-0.03, -0.01), 500, 500, 100, +1), "reversed (short quotes higher)")
        self.assertEqual(lt.verdict_dir((-0.01, 0.02), 500, 500, 100, +1), "no clear difference")
        self.assertEqual(lt.verdict_dir((-0.03, -0.01), 500, 500, 100, -1), "held (short quotes higher)")
        self.assertEqual(lt.verdict_dir((0.01, 0.03), 500, 500, 100, -1), "reversed (long quotes higher)")
        self.assertTrue(lt.verdict_dir((0.01, 0.03), 50, 500, 100, +1).startswith("underpowered"))
        self.assertTrue(lt.verdict_dir(None, 500, 500, 100, +1).startswith("underpowered"))


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.rows = [lt.length_row(ROW), lt.length_row(ROW2)]

    def test_analyse(self):
        res = lt.analyse(self.rows, reps=50)
        self.assertEqual(res["rows"], 2)
        self.assertEqual(res["totals"], {"n": 4, "prim_tight": 4, "wc": 2, "wc_tight": 2, "wc_loose": 0})
        self.assertEqual(set(res["tests"]),
                         {"A1_tight_changed_rate", "A2_loose_share_of_changed", "R0_loose_share_all"})
        for pid in lt.PREDICTED:  # tiny data -> underpowered
            self.assertTrue(res["tests"][pid]["verdict"].startswith("underpowered"), pid)
        self.assertEqual(res["tests"]["R0_loose_share_all"]["verdict"], "descriptive")
        self.assertEqual(res["tests"]["R0_loose_share_all"]["value"], 0.0)  # 0 loose of 2 changed
        self.assertFalse(res["consistent_with_earlier"])
        self.assertEqual(res["by_length"]["4-6"]["quotes"], 2)
        self.assertEqual(res["by_length"]["11-15"]["changed"], 2)


class EndToEndTests(unittest.TestCase):
    def test_main_writes_aggregates_only(self):
        recs = [{"conversation": [{"from": "human", "value": r["human"]}], "evaluation": r["evaluation"],
                 "reasoning": "", "band": r["band"], "generator": "g"} for r in (ROW, ROW2)]
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "sub")
            os.makedirs(data)
            with open(os.path.join(data, "glm47_final.jsonl"), "w", encoding="utf-8") as fh:
                for r in recs:
                    fh.write(json.dumps(r) + "\n")
            out = os.path.join(tmp, "length-tight.json")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = lt.main(["--data", tmp, "--out", out, "--reps", "50",
                              "--plan", os.path.join(tmp, "missing.md")])
            self.assertEqual(rc, 0)
            with open(out, encoding="utf-8") as fh:
                res = json.load(fh)
            dumped = json.dumps(res)
            for word in ("fox", "beach", "conclusion", "cat", "family", "river"):
                self.assertNotIn(word, dumped)
            self.assertEqual((res["rows"], res["records_read"]), (2, 2))
            self.assertEqual((res["totals"]["n"], res["totals"]["wc"]), (4, 2))
            self.assertNotIn("plan_sha256", res)
            self.assertIn('"n": 4', buf.getvalue())

    def test_missing_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(lt.main(["--data", tmp, "--out", os.path.join(tmp, "r.json")]), 2)


if __name__ == "__main__":
    unittest.main()
