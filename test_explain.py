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
"""Tests for explain.py. Every text here is made up; no dataset text is used."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import audit
import explain
import verbatim_quote_check as vqc

QUESTION = "Some people think exams are the best test. Discuss both views."
ESSAY = ("It is believed by some that exams is the best way to test student. "
         "In my opinion , they are not fair because students feel a lot of pressure. "
         "Students don't like them. This is a well known fact.\n\n"
         "To conclude, exams should be changed.")
HUMAN = QUESTION + "\n\n" + ESSAY

QUOTES = ["exams is the best way",                      # exact
          "exams **is** the best way",                  # emphasis
          "it is believed by some",                     # case
          "exams is the best ways to test student",     # changed words: spelling/form
          "they are fair because students feel",        # changed words: negation dropped
          "It is believed... exams is the best way",    # elision
          "exams **are** the best way to test student",  # changed words with emphasis
          "too short"]                                  # under 4 words
EVALUATION = "\n".join('You wrote "%s".' % q for q in QUOTES)
ROW = {"idx": 0, "band": "5.5", "human": HUMAN, "evaluation": EVALUATION,
       "reasoning": 'Hmm "exams is the best way" ok'}


def _rec(quote: str) -> dict:
    q, e, _ = audit.split_source(HUMAN)
    return audit.classify(e, vqc.words(e), q, quote, "You wrote ")


class NormaliseTests(unittest.TestCase):
    def test_spacing(self):
        self.assertEqual(explain._spacing("a ,b  c ( d ) e ."), "a, b c (d) e.")
        self.assertEqual(explain._spacing("1,000 and 2"), "1,000 and 2")
        self.assertEqual(explain._spacing("x... y"), "x... y")

    def test_fragments(self):
        self.assertEqual(explain.fragments("a b... c d […] e"), ["a b", "c d", "e"])
        self.assertEqual(explain.fragments("...a b..."), ["a b"])
        self.assertEqual(explain.fragments("a [...] b"), ["a", "b"])

    def test_in_order(self):
        self.assertTrue(explain.in_order(["ab", "d"], "abcd"))
        self.assertFalse(explain.in_order(["d", "ab"], "abcd"))
        self.assertFalse(explain.in_order([], "abcd"))

    def test_words_in_order(self):
        src = ["a", "b", "c", "d"]
        self.assertTrue(explain.words_in_order([["a", "b"], ["d"]], src))
        self.assertFalse(explain.words_in_order([["d"], ["a"]], src))
        self.assertFalse(explain.words_in_order([["a", "b", "c", "d", "e"]], src))
        self.assertFalse(explain.words_in_order([], src))


class FirstStepTests(unittest.TestCase):
    def setUp(self):
        self.eforms = explain.essay_forms(audit.split_source(HUMAN)[1])

    def step(self, quote):
        k = explain.first_step(quote, self.eforms)
        return None if k is None else explain.STEPS[k]

    def test_each_step(self):
        cases = {"exams is the best way": "exact",
                 "exams **is** the best way": "emphasis",
                 "Students don’t like them": "typography",
                 "In my opinion, they are not fair": "spacing",
                 "...a lot of pressure...": "edges",
                 "…a lot of pressure": "edges",
                 "it is believed by some": "case",
                 "It is believed... exams is the best way": "elision"}
        for quote, want in cases.items():
            self.assertEqual(self.step(quote), want, quote)

    def test_no_step(self):
        for quote in ("exams is the best way... It is believed", "This is a well-known fact",
                      "exams are the best way to test student"):
            self.assertIsNone(self.step(quote), quote)

    def test_step_zero_is_the_checker_exact_test(self):
        for quote in QUOTES:
            self.assertEqual(self.step(quote) == "exact", _rec(quote)["category"] == vqc.EXACT, quote)


class ExplainTests(unittest.TestCase):
    def setUp(self):
        self.essay = audit.split_source(HUMAN)[1]
        self.eforms = explain.essay_forms(self.essay)
        self.words = vqc.words(self.essay)

    def run_one(self, quote):
        return explain.explain(quote, _rec(quote), self.eforms, self.words)

    def test_other_punctuation(self):
        self.assertEqual(_rec("This is a well-known fact")["category"], vqc.PUNCT_WHITESPACE)
        self.assertEqual(self.run_one("This is a well-known fact"), ("other_punctuation", False, False))

    def test_elision_words(self):
        quote = "In my opinion they are... students feel"
        self.assertEqual(_rec(quote)["category"], vqc.ALTERED)
        self.assertEqual(self.run_one(quote), ("elision_words", True, False))

    def test_word_changed_flags(self):
        self.assertEqual(self.run_one("exams **are** the best way to test student"), ("word_changed", False, True))
        self.assertEqual(self.run_one("they are fair because students feel"), ("word_changed", False, False))


class KindTests(unittest.TestCase):
    def test_negation_dropped(self):
        k = explain.change_kinds({"quote": "they are fair because students feel",
                                  "passage": "they are not fair because students feel"})
        self.assertEqual(k, {"negation": True, "spelling_or_form": False, "word_swap": False,
                             "added_or_dropped": True})

    def test_spelling_and_swap(self):
        k = explain.change_kinds({"quote": "we go to the parks", "passage": "we go to the park"})
        self.assertEqual((k["spelling_or_form"], k["word_swap"]), (True, False))
        k = explain.change_kinds({"quote": "we go to the park", "passage": "we go to the garden"})
        self.assertEqual((k["spelling_or_form"], k["word_swap"], k["negation"]), (False, True, False))

    def test_kinds_from_checker_window(self):
        rec = _rec("exams is the best ways to test student")
        self.assertEqual(rec["passage"], "exams is the best way to test student")
        self.assertTrue(explain.change_kinds(rec)["spelling_or_form"])
        rec = _rec("they are fair because students feel")
        self.assertEqual(rec["passage"], "they are not fair because students feel")


class RowTests(unittest.TestCase):
    def test_explain_row_counts(self):
        out = explain.explain_row(ROW)
        ev = out["evaluation"]
        want = {"n": 7, "exact": 1, "emphasis": 1, "case": 1, "elision": 1, "word_changed": 3,
                "altered": 4, "altered_elision": 1, "wc_emphasis": 1, "wc_unmarked": 2, "wc_elided": 0,
                "wc_unmarked_plain": 2, "unmarked_negation": 1, "unmarked_spelling_or_form": 1,
                "unmarked_word_swap": 0, "unmarked_added_or_dropped": 1}
        for key in explain.COUNT_KEYS:
            self.assertEqual(ev[key], want.get(key, 0), key)
        self.assertEqual((out["reasoning"]["n"], out["reasoning"]["exact"]), (1, 1))
        self.assertEqual(len(out["review"]), 2)

    def test_summarise(self):
        s = explain.summarise([explain.explain_row(ROW)], "evaluation")
        self.assertAlmostEqual(s["matched_by_step"]["case"], 3 / 7)
        self.assertAlmostEqual(s["matched_by_step"]["elision"], 4 / 7)
        m = {k: v["value"] for k, v in s["measures"].items()}
        self.assertAlmostEqual(m["word_faithful_with_elision"], 4 / 7)
        self.assertAlmostEqual(m["word_changed_rate"], 3 / 7)
        self.assertAlmostEqual(m["unmarked_word_changed_rate"], 2 / 7)
        self.assertAlmostEqual(m["elision_share_of_altered"], 1 / 4)
        self.assertAlmostEqual(m["emphasis_share_of_word_changed"], 1 / 3)
        self.assertEqual(s["unmarked_kinds_share"], {"negation": 0.5, "spelling_or_form": 0.5,
                                                     "word_swap": 0.0, "added_or_dropped": 0.5})
        self.assertNotIn("ci95", s["measures"]["word_changed_rate"])

    def test_verdict(self):
        self.assertEqual(explain.verdict(0.85, 0.80, None, 400, 300), "held")
        self.assertEqual(explain.verdict(0.75, 0.80, None, 400, 300), "did not hold")
        self.assertEqual(explain.verdict(0.02, 0.01, 0.04, 400, 300), "held")
        self.assertEqual(explain.verdict(0.05, 0.01, 0.04, 400, 300), "did not hold")
        self.assertTrue(explain.verdict(0.5, 0.3, 0.7, 50, 100).startswith("underpowered"))


class EndToEndTests(unittest.TestCase):
    def test_main_writes_aggregates_only(self):
        rec = {"conversation": [{"from": "human", "value": HUMAN}], "evaluation": EVALUATION,
               "reasoning": ROW["reasoning"], "band": "5.5", "generator": "g"}
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "sub")
            os.makedirs(data)
            with open(os.path.join(data, "glm47_final.jsonl"), "w", encoding="utf-8") as fh:
                for _ in range(3):
                    fh.write(json.dumps(rec) + "\n")
            out = os.path.join(tmp, "explain.json")
            sample = os.path.join(tmp, "review.jsonl")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = explain.main(["--data", tmp, "--out", out, "--review-sample", sample, "--reps", "200",
                                   "--plan", os.path.join(tmp, "missing.md")])
            self.assertEqual(rc, 0)
            with open(out, encoding="utf-8") as fh:
                res = json.load(fh)
            dumped = json.dumps(res)
            for word in ("believed", "pressure", "exams"):
                self.assertNotIn(word, dumped)
            self.assertEqual((res["rows"], res["records_read"]), (3, 3))
            ev = res["evaluation"]
            self.assertEqual((ev["counts"]["n"], ev["counts"]["word_changed"]), (21, 9))
            self.assertFalse(ev["consistent_with_audit1"])
            self.assertIsNotNone(ev["measures"]["word_changed_rate"]["ci95"])
            self.assertTrue(res["predictions"]["P1"]["verdict"].startswith("underpowered"))
            self.assertNotIn("plan_sha256", res)
            with open(sample, encoding="utf-8") as fh:
                self.assertEqual(len(fh.readlines()), 6)
            self.assertIn('"n": 21', buf.getvalue())

    def test_missing_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(explain.main(["--data", tmp, "--out", os.path.join(tmp, "r.json")]), 2)


if __name__ == "__main__":
    unittest.main()
