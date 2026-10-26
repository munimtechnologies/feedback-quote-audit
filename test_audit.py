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
"""Tests for audit.py. Every text here is made up; no dataset text is used."""
from __future__ import annotations

import io
import json
import os
import random
import tempfile
import unittest
from contextlib import redirect_stdout

import audit
import verbatim_quote_check as vqc

QUESTION = "Some people think exams are the best test. Discuss both views."
ESSAY = ("It is believed by some that exams is the best way to test student. "
         "In my opinion they are not fair because students feel a lot of pressure.\n\n"
         "To conclude, exams should be changed.")
HUMAN = QUESTION + "\n\n" + ESSAY


class ExtractTests(unittest.TestCase):
    def test_straight_and_curly_quotes(self):
        text = 'You wrote "exams is the best way" and “they are not fair”.'
        self.assertEqual([q for q, _ in audit.extract_quotes(text)],
                         ["exams is the best way", "they are not fair"])

    def test_guillemets_and_low_high(self):
        text = "Bien: «hola mundo» y „guten Tag“."
        self.assertEqual([q for q, _ in audit.extract_quotes(text)], ["hola mundo", "guten Tag"])

    def test_quotes_do_not_cross_lines(self):
        self.assertEqual(audit.extract_quotes('a "b\nc" d'), [])

    def test_context_is_same_line_only(self):
        text = 'Better:\nOriginal: "exams is the best way"'
        (_, ctx), = audit.extract_quotes(text)
        self.assertEqual(ctx, "Original: ")

    def test_context_window_is_capped(self):
        text = "x" * 100 + '"abc"'
        (_, ctx), = audit.extract_quotes(text)
        self.assertEqual(len(ctx), audit.CUE_WINDOW)


class CueTests(unittest.TestCase):
    def test_rewrite_cues(self):
        for ctx in ("Improved version: ", "Better: ", "Revised: ", "you could write ", "→ ", "-> ",
                    "Instead, try ", "Suggested: ", "Correction: ", "it should be "):
            self.assertTrue(audit.CUE_RE.search(ctx), ctx)

    def test_original_is_not_a_cue(self):
        for ctx in ("Original: ", "You wrote ", "In your second paragraph, ", "the phrase "):
            self.assertFalse(audit.CUE_RE.search(ctx), ctx)

    def test_incorrect_is_not_correct(self):
        self.assertFalse(audit.CUE_RE.search("This is incorrect: "))


class SplitTests(unittest.TestCase):
    def test_blank_line_split(self):
        q, e, mode = audit.split_source(HUMAN)
        self.assertEqual((q, e, mode), (QUESTION, ESSAY, "blank_line"))

    def test_newline_split(self):
        q, e, mode = audit.split_source("Q?\nThe essay.")
        self.assertEqual((q, e, mode), ("Q?", "The essay.", "newline"))

    def test_whole_when_no_break(self):
        self.assertEqual(audit.split_source("Only one line."), ("", "Only one line.", "whole"))

    def test_trailing_blank_line_is_not_a_split(self):
        self.assertEqual(audit.split_source("Only text.\n\n"), ("", "Only text.\n\n", "whole"))


class WindowTests(unittest.TestCase):
    def test_best_window_ratio_equals_checker(self):
        rng = random.Random(7)
        src = vqc.words(ESSAY)
        for _ in range(200):
            i = rng.randrange(len(src))
            q = src[i:i + rng.randint(1, 8)]
            if q and rng.random() < 0.7:
                q[rng.randrange(len(q))] = rng.choice(["the", "exam", "zzz", "are"])
            _, _, r = audit.best_window(src, q)
            self.assertEqual(r, vqc._best_ratio(src, q))

    def test_word_edits(self):
        self.assertEqual(audit.word_edits(["exams", "is", "the"], ["exams", "are", "the"]), 1)
        self.assertEqual(audit.word_edits(["a", "b", "c"], ["a", "c"]), 1)
        self.assertEqual(audit.word_edits(["a", "b"], ["a", "b"]), 0)


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self.q, self.e, _ = audit.split_source(HUMAN)
        self.w = vqc.words(self.e)

    def test_exact(self):
        r = audit.classify(self.e, self.w, self.q, "exams is the best way to test student", "You wrote ")
        self.assertEqual((r["category"], r["n_words"], r["cue"], r["question"]), (vqc.EXACT, 8, False, False))
        self.assertNotIn("quote", r)

    def test_silent_correction_is_altered_with_one_edit(self):
        r = audit.classify(self.e, self.w, self.q, "exams are the best way to test student", "Original: ")
        self.assertEqual(r["category"], vqc.ALTERED)
        self.assertEqual(r["edits"], 1)
        self.assertEqual(r["passage"], "exams is the best way to test student")
        self.assertTrue(audit.in_primary(r))

    def test_cued_rewrite_is_excluded(self):
        r = audit.classify(self.e, self.w, self.q, "exams are the best way to test students", "Better: ")
        self.assertTrue(r["cue"])
        self.assertFalse(audit.in_primary(r))

    def test_question_quote_is_excluded(self):
        r = audit.classify(self.e, self.w, self.q, "exams are the best test", "The task says ")
        self.assertTrue(r["question"])
        self.assertFalse(audit.in_primary(r))

    def test_short_quote_is_excluded(self):
        r = audit.classify(self.e, self.w, self.q, "exams is", "")
        self.assertEqual(r["category"], vqc.EXACT)
        self.assertFalse(audit.in_primary(r))

    def test_max_words(self):
        r = audit.classify(self.e, self.w, self.q, "exams is the best way to test student", "")
        self.assertTrue(audit.in_primary(r, 8))
        self.assertFalse(audit.in_primary(r, 7))


class RowTests(unittest.TestCase):
    def test_to_row_uses_human_turn(self):
        rec = {"conversation": [{"from": "human", "value": HUMAN}, {"from": "gpt", "value": "x"}],
               "topic": "other", "evaluation": "e", "reasoning": "r", "band": "6.0", "generator": "g"}
        row = audit.to_row(3, rec)
        self.assertEqual((row["idx"], row["human"], row["evaluation"], row["band"]), (3, HUMAN, "e", "6.0"))

    def test_to_row_falls_back_to_topic(self):
        self.assertEqual(audit.to_row(0, {"topic": HUMAN})["human"], HUMAN)

    def test_audit_row(self):
        row = {"idx": 0, "band": "6.0", "human": HUMAN, "reasoning": 'Hmm "exams is the best way to test student".',
               "evaluation": 'Original: "exams are the best way to test student" and "students feel a lot of pressure".'}
        out = audit.audit_row(row)
        self.assertEqual(out["mode"], "blank_line")
        self.assertEqual([r["category"] for r in out["evaluation"]], [vqc.ALTERED, vqc.EXACT])
        self.assertEqual([r["category"] for r in out["reasoning"]], [vqc.EXACT])

    def test_parse_band(self):
        self.assertEqual(audit.parse_band("6.5"), 6.5)
        self.assertEqual(audit.parse_band("<4"), 3.5)
        self.assertIsNone(audit.parse_band(None))
        self.assertIsNone(audit.parse_band("n/a"))


class ReadTests(unittest.TestCase):
    RECS = [{"id": "a", "evaluation": "x"}, {"id": "b", "evaluation": "y “z”"}]

    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_jsonl(self):
        path = self._write("\n".join(json.dumps(r) for r in self.RECS) + "\n\n")
        self.assertEqual(list(audit.iter_records(path)), self.RECS)

    def test_json_array_small_chunks(self):
        path = self._write(" [\n" + ",\n".join(json.dumps(r) for r in self.RECS) + "\n]\n")
        with open(path, encoding="utf-8") as fh:
            self.assertEqual(list(audit._iter_json_array(fh, chunk=3)), self.RECS)
        self.assertEqual(list(audit.iter_records(path)), self.RECS)


class StatsTests(unittest.TestCase):
    def test_ratio(self):
        self.assertEqual(audit.ratio([(1, 2), (3, 2)]), 1.0)
        self.assertIsNone(audit.ratio([(0, 0)]))

    def test_boot_ratio_constant(self):
        lo, hi = audit.boot_ratio([(9, 10)] * 20, random.Random(1), reps=200)
        self.assertAlmostEqual(lo, 0.9)
        self.assertAlmostEqual(hi, 0.9)

    def test_boot_group_diff_sign(self):
        lo, hi = audit.boot_group_diff([(5, 10)] * 30, [(9, 10)] * 30, random.Random(1), reps=200)
        self.assertLess(hi, 0)
        self.assertAlmostEqual(lo, -0.4)

    def test_boot_paired_diff(self):
        lo, hi = audit.boot_paired_diff([(8, 10, 10, 10)] * 30, random.Random(1), reps=200)
        self.assertAlmostEqual(lo, -0.2)
        self.assertAlmostEqual(hi, -0.2)

    def test_boot_empty(self):
        self.assertIsNone(audit.boot_ratio([(0, 0)], random.Random(1), reps=10))

    def test_verdicts(self):
        self.assertTrue(audit.verdict_level(0.96, 400).startswith("H1 held"))
        self.assertTrue(audit.verdict_level(0.94, 400).startswith("H1 did not hold"))
        self.assertTrue(audit.verdict_level(0.99, 10).startswith("underpowered"))
        self.assertTrue(audit.verdict_diff((-0.05, -0.01), 200, 200, 100, "H2").startswith("H2 held"))
        self.assertTrue(audit.verdict_diff((0.01, 0.05), 200, 200, 100, "H2").startswith("H2 reversed"))
        self.assertTrue(audit.verdict_diff((-0.01, 0.05), 200, 200, 100, "H2").startswith("no clear"))
        self.assertTrue(audit.verdict_diff((-0.05, -0.01), 50, 200, 100, "H2").startswith("underpowered"))


class EndToEndTests(unittest.TestCase):
    def test_main_writes_aggregates_only(self):
        rec = {"conversation": [{"from": "human", "value": HUMAN}],
               "evaluation": 'Original: "exams are the best way to test student". You wrote '
                             '"students feel a lot of pressure". Better: "exams are the best way to test students".',
               "reasoning": '<think>"In my opinion they are not fair"</think>', "band": "5.5", "generator": "g"}
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "sub")
            os.makedirs(data)
            with open(os.path.join(data, "glm47_final.jsonl"), "w", encoding="utf-8") as fh:
                for _ in range(3):
                    fh.write(json.dumps(rec) + "\n")
            out = os.path.join(tmp, "results.json")
            sample = os.path.join(tmp, "review.jsonl")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = audit.main(["--data", tmp, "--out", out, "--review-sample", sample,
                                 "--prereg", os.path.join(tmp, "missing.md")])
            self.assertEqual(rc, 0)
            with open(out, encoding="utf-8") as fh:
                res = json.load(fh)
            self.assertNotIn("pressure", json.dumps(res))
            ev = res["evaluation"]
            self.assertEqual(res["rows"], 3)
            self.assertEqual(res["records_read"], 3)
            self.assertEqual(ev["quotes"], 9)
            self.assertEqual(ev["excluded_cue"], 3)
            self.assertEqual(ev["primary_matched"], 6)
            self.assertAlmostEqual(ev["exact_rate"], 0.5)
            self.assertEqual(ev["altered_word_edits"], {"1": 3})
            self.assertTrue(res["H1"].startswith("underpowered"))
            self.assertEqual(res["H2_band"]["low_band_essays"], 3)
            self.assertEqual(res["H3_reasoning_vs_evaluation"]["reasoning_exact_rate"], 1.0)
            self.assertNotIn("prereg_sha256", res)
            with open(sample, encoding="utf-8") as fh:
                lines = [json.loads(x) for x in fh]
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[0]["edits"], 1)
            self.assertIn('"rows": 3', buf.getvalue())

    def test_missing_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(audit.main(["--data", tmp, "--out", os.path.join(tmp, "r.json")]), 2)


if __name__ == "__main__":
    unittest.main()
