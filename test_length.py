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
"""Tests for length.py. Every text here is made up; no dataset text is used."""
from __future__ import annotations

import io
import json
import os
import random
import tempfile
import unittest
from contextlib import redirect_stdout

import length

QUESTION = "Some people think exams are the best test. Discuss both views."
ESSAY = ("It is believed by some that exams is the best way to test student. "
         "In my opinion , they are not fair because students feel a lot of pressure. "
         "Students don't like them. This is a well known fact.\n\n"
         "To conclude, exams should be changed.")
QUOTES = ["exams is the best way",                      # 5 words, exact
          "exams **is** the best way",                  # 5, emphasis
          "it is believed by some",                     # 5, case
          "exams is the best ways to test student",     # 8, changed, unmarked, 1 edit
          "they are fair because students feel",        # 6, changed, unmarked, 1 edit
          "It is believed... exams is the best way",    # 8, elision
          "exams **are** the best way to test student",  # 8, changed, marked, 1 edit
          "too short"]                                  # under 4 words
ROW = {"idx": 0, "band": "5.5", "human": QUESTION + "\n\n" + ESSAY,
       "evaluation": "\n".join('You wrote "%s".' % q for q in QUOTES), "reasoning": ""}

QUESTION2 = "Do children spend too much time on screens? Give your opinion."
SENTENCE = ("Many young people today spend most of their free time looking at small screens instead of "
            "reading books or playing sports with their friends in the park after school every day")
QUOTES2 = [SENTENCE,                                    # 31 words, exact
           SENTENCE.replace("looking", "staring"),      # 31, changed, unmarked, 1 edit
           "small screens instead of reading"]          # 5, exact
ROW2 = {"idx": 1, "band": "7.5", "human": QUESTION2 + "\n\n" + SENTENCE + ".",
        "evaluation": "\n".join('You wrote "%s".' % q for q in QUOTES2), "reasoning": ""}

WANT = {"n": [4, 3, 0, 0, 0], "words": [21, 24, 0, 0, 0], "exact": [1, 0, 0, 0, 0],
        "formatting": [2, 0, 0, 0, 0], "changed": [1, 2, 0, 0, 0], "unmarked": [1, 1, 0, 0, 0],
        "edits": [1, 2, 0, 0, 0]}
WANT2 = {"n": [1, 0, 0, 0, 2], "words": [5, 0, 0, 0, 62], "exact": [1, 0, 0, 0, 1],
         "formatting": [0, 0, 0, 0, 0], "changed": [0, 0, 0, 0, 1], "unmarked": [0, 0, 0, 0, 1],
         "edits": [0, 0, 0, 0, 1]}


class BinTests(unittest.TestCase):
    def test_bin_of(self):
        cases = {3: None, 4: 0, 6: 0, 7: 1, 10: 1, 11: 2, 15: 2, 16: 3, 25: 3, 26: 4, 300: 4}
        for n, want in cases.items():
            self.assertEqual(length.bin_of(n), want, n)
        self.assertEqual(len(length.BINS), len(length.BIN_NAMES))
        self.assertEqual(sorted(b for s in length.STRATA for b in s), list(range(len(length.BINS))))


class RowTests(unittest.TestCase):
    def test_length_row(self):
        out = length.length_row(ROW)
        self.assertEqual(out["band"], 5.5)
        for key in length.KEYS:
            self.assertEqual(out[key], WANT[key], key)

    def test_long_quotes(self):
        out = length.length_row(ROW2)
        self.assertEqual(out["band"], 7.5)
        for key in length.KEYS:
            self.assertEqual(out[key], WANT2[key], key)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.rows = [length.length_row(ROW), length.length_row(ROW2)]

    def test_long_minus_short(self):
        t = length.long_minus_short(self.rows, "changed", "n", random.Random(1), 200)
        self.assertAlmostEqual(t["long"], 1 / 2)
        self.assertAlmostEqual(t["short"], 1 / 5)
        self.assertAlmostEqual(t["diff"], 0.3)
        self.assertEqual((t["long_quotes"], t["short_quotes"]), (2, 5))
        self.assertIsNotNone(t["diff_ci95"])
        t = length.long_minus_short(self.rows, "edits", "words", random.Random(1), 200)
        self.assertAlmostEqual(t["long"], 1 / 62)
        self.assertAlmostEqual(t["short"], 1 / 26)

    def test_weights_and_std_rate(self):
        w = length.weights(self.rows)
        self.assertEqual([round(x, 6) for x in w], [0.8, 0.0, 0.2])
        both = length.strata_rows(self.rows, "changed")
        self.assertAlmostEqual(length.std_rate(both, w), 0.8 * 3 / 8 + 0.2 * 1 / 2)
        self.assertAlmostEqual(length.std_rate(length.strata_rows(self.rows[1:], "changed"), w), 0.1)
        self.assertIsNone(length.std_rate(length.strata_rows(self.rows[:1], "changed"), w))
        self.assertEqual(length.weights([]), [0.0, 0.0, 0.0])

    def test_band_compare_underpowered(self):
        w = length.weights(self.rows)
        t = length.band_compare(self.rows, "changed", w, random.Random(1), 50)
        self.assertEqual((t["low_essays"], t["high_essays"]), (1, 1))
        self.assertEqual((t["low_quotes"], t["high_quotes"]), (7, 3))
        self.assertAlmostEqual(t["raw_diff"], 3 / 7 - 1 / 3)
        self.assertIsNone(t["low_std"])
        self.assertIsNone(t["std_diff_ci95"])
        self.assertEqual(t["smallest_stratum_quotes"], 0)

    def test_boot_std_diff(self):
        w = [0.5, 0.0, 0.5]
        a = [(1, 2, 0, 0, 1, 2)] * 5
        b = [(0, 2, 0, 0, 0, 2)] * 5
        self.assertEqual(length.boot_std_diff(a, b, w, random.Random(1), 20), (0.5, 0.5))
        self.assertIsNone(length.boot_std_diff([], b, w, random.Random(1), 20))

    def test_verdict_up(self):
        self.assertEqual(length.verdict_up((0.01, 0.03), 500, 300), "held (difference above zero)")
        self.assertEqual(length.verdict_up((-0.03, -0.01), 500, 300), "reversed (difference below zero)")
        self.assertEqual(length.verdict_up((-0.01, 0.02), 500, 300), "no clear difference")
        self.assertTrue(length.verdict_up((0.01, 0.03), 200, 300).startswith("underpowered"))
        self.assertTrue(length.verdict_up(None, 500, 300).startswith("underpowered"))

    def test_analyse(self):
        res = length.analyse(self.rows, reps=50)
        self.assertEqual(res["totals"]["n"], 10)
        self.assertEqual(res["totals"]["changed"], 4)
        self.assertEqual(res["by_length"]["26+"]["quotes"], 2)
        self.assertAlmostEqual(res["by_length"]["4-6"]["formatting_rate"], 2 / 5)
        self.assertIsNone(res["by_length"]["11-15"]["changed_rate"])
        self.assertEqual(set(res["tests"]), {"L1", "L2", "L3", "B1", "B2", "B3", "B4"})
        for pid in length.PREDICTED:
            self.assertTrue(res["tests"][pid]["verdict"].startswith("underpowered"), pid)
        self.assertEqual(res["tests"]["B3"]["verdict"], "descriptive")
        self.assertFalse(res["consistent_with_earlier"])


class EndToEndTests(unittest.TestCase):
    def test_main_writes_aggregates_only(self):
        recs = [{"conversation": [{"from": "human", "value": r["human"]}], "evaluation": r["evaluation"],
                 "reasoning": "", "band": r["band"], "generator": "g"} for r in (ROW, ROW2)]
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "sub")
            os.makedirs(data)
            with open(os.path.join(data, "glm47_final.jsonl"), "w", encoding="utf-8") as fh:
                for rec in recs + recs:
                    fh.write(json.dumps(rec) + "\n")
            out = os.path.join(tmp, "length.json")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = length.main(["--data", tmp, "--out", out, "--reps", "50",
                                  "--plan", os.path.join(tmp, "missing.md")])
            self.assertEqual(rc, 0)
            with open(out, encoding="utf-8") as fh:
                res = json.load(fh)
            dumped = json.dumps(res)
            for word in ("believed", "pressure", "screens", "staring"):
                self.assertNotIn(word, dumped)
            self.assertEqual((res["rows"], res["records_read"]), (4, 4))
            self.assertEqual((res["totals"]["n"], res["totals"]["changed"]), (20, 8))
            self.assertNotIn("plan_sha256", res)
            self.assertIn('"n": 20', buf.getvalue())

    def test_missing_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(length.main(["--data", tmp, "--out", os.path.join(tmp, "r.json")]), 2)


if __name__ == "__main__":
    unittest.main()
