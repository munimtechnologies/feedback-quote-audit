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
"""Tests for band.py. Every text here is made up; no dataset text is used."""
from __future__ import annotations

import io
import json
import os
import random
import tempfile
import unittest
from contextlib import redirect_stdout

import audit
import band
import verbatim_quote_check as vqc

QUESTION = "Describe a time you learned something new. Give details and examples."
ESSAY = ("The quick brown fox jumps over the lazy dog. "
         "My family went to the beach last summer for a week. "
         "It was the best day of the whole year.\n\n"
         "In conclusion, I learned a lot from this trip.")
# 1: 8-word exact substring -> primary, tight. 2: exact but rewrite-cued -> excluded. 3: under 4 words.
# 4: one word swapped (fox -> cat) in a 9-word span -> altered, tight, word-changed.
QUOTES = ['You wrote "My family went to the beach last summer".',
          'Instead, you could write "It was the best day of the whole year".',
          'You wrote "the lazy dog".',
          'You wrote "The quick brown cat jumps over the lazy dog".']
ROW = {"idx": 0, "band": "5.0", "human": QUESTION + "\n\n" + ESSAY,
       "evaluation": "\n".join(QUOTES), "reasoning": ""}
ROW_HIGH = {**ROW, "idx": 1, "band": "8.0"}

# eligible=1,2,4 (3 is too short); cue_excl=2; primary n=1,4; prim_tight=1,4; wc=4; wc_tight=4.
WANT = {"eligible": 3, "cue_excl": 1, "n": 2, "prim_tight": 2, "wc": 1, "wc_tight": 1, "wc_loose": 0}


def rec(category, n_words, similarity, cue=False, question=False):
    return {"category": category, "n_words": n_words, "similarity": similarity,
            "cue": cue, "question": question, "edits": None}


class BucketsTests(unittest.TestCase):
    def test_not_counted(self):
        self.assertEqual(band.buckets(rec(vqc.NOT_FOUND, 8, 0.3), None), dict.fromkeys(band.KEYS, 0))
        self.assertEqual(band.buckets(rec(vqc.EXACT, 3, 1.0), "exact"), dict.fromkeys(band.KEYS, 0))

    def test_cue_and_question_excluded(self):
        b = band.buckets(rec(vqc.ALTERED, 6, 0.9, cue=True), "word_changed")
        self.assertEqual((b["eligible"], b["cue_excl"], b["n"], b["wc"]), (1, 1, 0, 0))
        b = band.buckets(rec(vqc.ALTERED, 6, 0.9, question=True), "word_changed")
        self.assertEqual((b["eligible"], b["cue_excl"], b["n"], b["wc"]), (1, 0, 0, 0))

    def test_exact_primary(self):
        b = band.buckets(rec(vqc.EXACT, 8, 1.0), "exact")
        self.assertEqual((b["eligible"], b["n"], b["prim_tight"], b["wc"]), (1, 1, 1, 0))

    def test_changed_tight_and_loose(self):
        hi = band.buckets(rec(vqc.ALTERED, 9, 0.9), "word_changed")
        self.assertEqual((hi["n"], hi["prim_tight"], hi["wc"], hi["wc_tight"], hi["wc_loose"]),
                         (1, 1, 1, 1, 0))
        lo = band.buckets(rec(vqc.ALTERED, 6, 0.7), "word_changed")
        self.assertEqual((lo["n"], lo["prim_tight"], lo["wc"], lo["wc_tight"], lo["wc_loose"]),
                         (1, 0, 1, 0, 1))
        edge = band.buckets(rec(vqc.ALTERED, 6, band.TIGHT), "word_changed")  # exactly 0.8 is tight
        self.assertEqual((edge["wc_tight"], edge["wc_loose"]), (1, 0))

    def test_changed_only_for_word_changed(self):
        b = band.buckets(rec(vqc.ALTERED, 7, 0.7), "elision_words")
        self.assertEqual((b["n"], b["wc"], b["wc_loose"]), (1, 0, 0))


class RowTests(unittest.TestCase):
    def test_band_row(self):
        out = band.band_row(ROW)
        self.assertEqual(out["band"], 5.0)
        for key in band.KEYS:
            self.assertEqual(out[key], WANT[key], key)
        self.assertEqual(out["wc_tight"] + out["wc_loose"], out["wc"])


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.rows = [band.band_row(ROW), band.band_row(ROW_HIGH)]

    def test_verdict_dir(self):
        self.assertEqual(band.verdict_dir((0.01, 0.03), 500, 500, 100, +1), "held (weak essays higher)")
        self.assertEqual(band.verdict_dir((-0.03, -0.01), 500, 500, 100, +1),
                         "reversed (strong essays higher)")
        self.assertEqual(band.verdict_dir((-0.01, 0.02), 500, 500, 100, +1), "no clear difference")
        self.assertEqual(band.verdict_dir((-0.03, -0.01), 500, 500, 100, -1), "held (strong essays higher)")
        self.assertEqual(band.verdict_dir((0.01, 0.03), 500, 500, 100, -1), "reversed (weak essays higher)")
        self.assertTrue(band.verdict_dir((0.01, 0.03), 50, 500, 100, +1).startswith("underpowered"))
        self.assertTrue(band.verdict_dir(None, 500, 500, 100, +1).startswith("underpowered"))

    def test_analyse(self):
        res = band.analyse(self.rows, reps=50)
        self.assertEqual(res["rows"], 2)
        self.assertEqual(res["low_essays"], 1)
        self.assertEqual(res["high_essays"], 1)
        self.assertEqual(res["totals"]["n"], 4)
        self.assertEqual(res["totals"]["wc"], 2)
        self.assertEqual(set(res["tests"]),
                         {"T1_cue_exclusion", "T2_changed_rate_tight", "T3_loose_share_of_changed",
                          "R0_changed_rate_all"})
        for pid in band.PREDICTED:
            self.assertTrue(res["tests"][pid]["verdict"].startswith("underpowered"), pid)
        self.assertEqual(res["tests"]["R0_changed_rate_all"]["verdict"], "descriptive")
        self.assertFalse(res["consistent_with_earlier"])


class EndToEndTests(unittest.TestCase):
    def test_main_writes_aggregates_only(self):
        recs = [{"conversation": [{"from": "human", "value": r["human"]}], "evaluation": r["evaluation"],
                 "reasoning": "", "band": r["band"], "generator": "g"} for r in (ROW, ROW_HIGH)]
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "sub")
            os.makedirs(data)
            with open(os.path.join(data, "glm47_final.jsonl"), "w", encoding="utf-8") as fh:
                for r in recs:
                    fh.write(json.dumps(r) + "\n")
            out = os.path.join(tmp, "band.json")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = band.main(["--data", tmp, "--out", out, "--reps", "50",
                                "--plan", os.path.join(tmp, "missing.md")])
            self.assertEqual(rc, 0)
            with open(out, encoding="utf-8") as fh:
                res = json.load(fh)
            dumped = json.dumps(res)
            for word in ("fox", "beach", "conclusion", "cat", "family"):
                self.assertNotIn(word, dumped)
            self.assertEqual((res["rows"], res["records_read"]), (2, 2))
            self.assertEqual((res["totals"]["n"], res["totals"]["wc"]), (4, 2))
            self.assertNotIn("plan_sha256", res)
            self.assertIn('"n": 4', buf.getvalue())

    def test_missing_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(band.main(["--data", tmp, "--out", os.path.join(tmp, "r.json")]), 2)


if __name__ == "__main__":
    unittest.main()
