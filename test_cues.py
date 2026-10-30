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
"""Tests for cues.py (audit 5b). Made-up essays and feedback only; no SpecEval text."""
import json
import os
import tempfile
import unittest

import audit
import cues
import speceval
import verbatim_quote_check as vqc

ESSAY = ("My summer job taught me patience and careful planning every day.\n\n"
         "Working at the library showed me how quiet spaces help people think clearly.")
TOP = "\n".join([
    'You open with "My summer job taught me patience" and it works.',            # primary, exact, short
    'Later "how quiet spaces help people think" links back.',                    # primary, exact, short
    'Here "My summer job taught me patience and careful plans every day" is unclear.',  # primary, changed, long
    'Instead "My job made me patient and organised" reads well.',                 # not found
    'Also "summer job" is vague.',                                                # under four words
    'For example, "Working at the library showed me how quiet spaces" is vivid.',  # cited, exact, 9 words
])
MIDDLE = 'For example, a better start is "My summer job taught me patience" here.'  # edit-cued, exact, short
BOTTOM = "\n".join([
    'You could write "My summer job taught me patience and careful plans every day" instead.',  # edit, changed, long
    'You write "Working at the library showed me how quiet spaces" well.',         # primary, exact, 9 words
])


def counts(**kw) -> dict:
    c = dict.fromkeys(cues.KEYS, 0)
    c.update(kw)
    return c


def records() -> list:
    return [
        {"essay_id": 1, "essay_set": 1, "essay": ESSAY, "chosen": TOP, "rejected": MIDDLE,
         "chosen_score": 0.9, "rejected_score": 0.1, "split": "train"},
        {"essay_id": 1, "essay_set": 1, "essay": ESSAY, "chosen": MIDDLE, "rejected": BOTTOM,
         "chosen_score": 0.1, "rejected_score": 0.0, "split": "train"},
    ]


class GroupTest(unittest.TestCase):
    def rec(self, cue: bool, n_words: int = 5, category=vqc.EXACT) -> dict:
        return {"category": category, "n_words": n_words, "cue": cue, "question": False}

    def test_group(self):
        self.assertEqual(cues.group(self.rec(False), "You write "), "primary")
        self.assertEqual(cues.group(self.rec(True), "For example, "), "cited")
        self.assertEqual(cues.group(self.rec(True), "such as "), "cited")
        self.assertEqual(cues.group(self.rec(True), "as in e.g. "), "cited")
        self.assertEqual(cues.group(self.rec(True), "Instead "), "edit")
        self.assertEqual(cues.group(self.rec(True), "For example, a better start is "), "edit")
        self.assertIsNone(cues.group(self.rec(False, n_words=3), ""))
        self.assertIsNone(cues.group(self.rec(False, category=vqc.NOT_FOUND), ""))

    def test_primary_matches_audit(self):
        for cue in (False, True):
            for n in (3, 4, 9):
                for cat in (vqc.EXACT, vqc.ALTERED, vqc.NOT_FOUND):
                    r = self.rec(cue, n, cat)
                    self.assertEqual(cues.group(r, "For example, ") == "primary", audit.in_primary(r))


class CountsTest(unittest.TestCase):
    def test_essay_rows(self):
        essays, _ = speceval.collect(records())
        rows = {r["rank"]: r["counts"] for r in cues.essay_rows("1", essays["1"])}
        self.assertEqual(rows["top"], counts(
            feedback=1, quotes=6, matched4=4,
            n_primary=3, wc_primary=1, n_short_primary=2, n_long_primary=1, wc_long_primary=1, texts_primary=1,
            n_cited=1, texts_cited=1,
            n_wide=4, wc_wide=1, n_short_wide=2, n_long_wide=1, wc_long_wide=1, texts_wide=1))
        self.assertEqual(rows["middle"], counts(feedback=1, quotes=1, matched4=1, n_edit=1, n_short_edit=1,
                                                texts_edit=1))
        self.assertEqual(rows["bottom"], counts(
            feedback=1, quotes=2, matched4=2,
            n_edit=1, wc_edit=1, n_long_edit=1, wc_long_edit=1, texts_edit=1,
            n_primary=1, texts_primary=1, n_wide=1, texts_wide=1))


class AnalyseTest(unittest.TestCase):
    def rows(self, essays: int) -> list:
        out = []
        for i in range(essays):
            e = "E%04d" % i
            out.append({"essay": e, "set": "1", "rank": "top", "counts": counts(
                feedback=1, n_primary=2, n_cited=2, n_wide=4, n_edit=2, wc_edit=1)})
            out.append({"essay": e, "set": "1", "rank": "bottom", "counts": counts(
                feedback=1, n_primary=2, wc_primary=1, n_cited=2, wc_cited=1, n_wide=4, wc_wide=2)})
        return out

    def test_verdicts(self):
        res = cues.analyse(self.rows(150), reps=200)
        t = res["tests"]
        self.assertEqual(res["essays"], 150)
        self.assertEqual(t["G1_cited_vs_primary_count"]["verdict"], "held")
        self.assertAlmostEqual(t["G2_cited_vs_primary_rate"]["diff"], 0.0)
        self.assertTrue(t["G2_cited_vs_primary_rate"]["verdict"].startswith("held"))
        self.assertAlmostEqual(t["G3_edit_vs_cited"]["diff"], 0.25)
        self.assertEqual(t["G3_edit_vs_cited"]["verdict"], "held (edit-cued higher)")
        self.assertEqual(t["G3_edit_vs_cited"]["denominators"], [300, 600])
        self.assertAlmostEqual(t["G4_bottom_vs_top_wide"]["diff"], 0.5)
        self.assertEqual(t["G4_bottom_vs_top_wide"]["verdict"], "held (bottom-ranked higher)")
        self.assertAlmostEqual(res["pooled"]["primary"]["word_changed_rate"], 0.25)
        self.assertAlmostEqual(res["by_rank"]["top"]["wide"]["word_changed_rate"], 0.0)
        self.assertIsNone(res["by_rank"]["middle"]["primary"]["word_changed_rate"])

    def test_underpowered(self):
        res = cues.analyse(self.rows(20), reps=50)
        for name in ("G2_cited_vs_primary_rate", "G3_edit_vs_cited", "G4_bottom_vs_top_wide"):
            self.assertTrue(res["tests"][name]["verdict"].startswith("underpowered"), name)

    def test_band(self):
        self.assertTrue(cues.verdict_band((-0.02, 0.02), 500, 500, 100).startswith("held"))
        self.assertEqual(cues.verdict_band((0.04, 0.1), 500, 500, 100), "did not hold")
        self.assertEqual(cues.verdict_band((-0.1, -0.04), 500, 500, 100), "did not hold")
        self.assertEqual(cues.verdict_band((-0.05, 0.01), 500, 500, 100), "inconclusive")
        self.assertTrue(cues.verdict_band((-0.01, 0.01), 50, 500, 100).startswith("underpowered"))


class EndToEndTest(unittest.TestCase):
    def test_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "speceval_dataset.json")
            with open(data, "w", encoding="utf-8") as fh:
                json.dump(records(), fh)
            out = os.path.join(tmp, "cues.json")
            self.assertEqual(cues.main(["--data", tmp, "--out", out, "--reps", "20",
                                        "--plan", os.path.join(tmp, "none.md")]), 0)
            with open(out, encoding="utf-8") as fh:
                res = json.load(fh)
        c = res["pooled"]["counts"]
        self.assertEqual(res["records"], 2)
        self.assertEqual(res["feedback_texts"], 3)
        self.assertEqual((c["n_primary"], c["wc_primary"], c["n_cited"], c["n_edit"], c["wc_edit"], c["n_wide"]),
                         (4, 1, 1, 2, 1, 5))
        self.assertEqual(res["tests"]["G1_cited_vs_primary_count"]["verdict"], "did not hold")
        self.assertFalse(res["sha256_as_probed"])
        self.assertNotIn("plan_sha256", res)
        text = json.dumps(res)
        for phrase in ("summer job", "quiet spaces", "library", "patience"):
            self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
