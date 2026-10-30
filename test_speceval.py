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
"""Tests for speceval.py (audit 5). Made-up essays and feedback only; no SpecEval text."""
import json
import os
import tempfile
import unittest

import speceval

ESSAY = ("My summer job taught me patience and careful planning every day.\n\n"
         "Working at the library showed me how quiet spaces help people think clearly.")
TOP = "\n".join([
    'You open with "My summer job taught me patience" and it works.',            # exact
    'Later "how quiet spaces help people think" links back.',                    # exact
    'Here "My summer job taught me patience and careful plans every day" is unclear.',  # one word changed
    'Instead "My job made me patient and organised" reads well.',                 # rewrite cue
    'Also "summer job" is vague.',                                                # under four words
])
MIDDLE = "Good detail about the library."
BOTTOM = 'You write "Working at the library showed me how quiet spaces" well.'   # exact, 9 words
ESSAY2 = "The bridge was built in 1990 by local workers."
OTHER = 'It says "The bridge was built in 1991 by local workers" here.'          # one word changed, 9 words


def counts(**kw) -> dict:
    c = dict.fromkeys(speceval.KEYS, 0)
    c.update(kw)
    return c


def records() -> list:
    return [
        {"essay_id": 1, "essay_set": 1, "essay": ESSAY, "chosen": TOP, "rejected": MIDDLE,
         "chosen_score": 0.9, "rejected_score": 0.1, "split": "train"},
        {"essay_id": 1, "essay_set": 1, "essay": ESSAY, "chosen": MIDDLE, "rejected": BOTTOM,
         "chosen_score": 0.1, "rejected_score": 0.0, "split": "train"},
        {"essay_id": 9, "essay_set": 2, "chosen": TOP, "rejected": MIDDLE, "split": "train"},
        {"essay_id": 2, "essay_set": 3, "essay": ESSAY2, "chosen": OTHER, "rejected": "",
         "chosen_score": 0.5, "rejected_score": 0.0, "split": "valid"},
    ]


class RankTest(unittest.TestCase):
    def test_rank(self):
        self.assertEqual(speceval.rank(2, 0), "top")
        self.assertEqual(speceval.rank(0, 1), "bottom")
        self.assertEqual(speceval.rank(1, 1), "middle")


class CollectTest(unittest.TestCase):
    def test_collect(self):
        essays, info = speceval.collect(records())
        self.assertEqual(info, {"records": 4, "skipped_records": 1, "essay_text_conflicts": 0,
                                "splits": {"train": 2, "valid": 1}})
        self.assertEqual(sorted(essays), ["1", "2"])
        self.assertEqual(essays["1"]["feedback"], {TOP: [1, 0], MIDDLE: [1, 1], BOTTOM: [0, 1]})
        self.assertEqual(essays["2"]["feedback"], {OTHER: [1, 0]})
        self.assertEqual(essays["2"]["set"], "3")

    def test_conflict(self):
        recs = records()[:2]
        recs[1] = dict(recs[1], essay=ESSAY2)
        _, info = speceval.collect(recs)
        self.assertEqual(info["essay_text_conflicts"], 1)


class CountsTest(unittest.TestCase):
    def test_essay_rows(self):
        essays, _ = speceval.collect(records())
        rows = {r["rank"]: r["counts"] for r in speceval.essay_rows("1", essays["1"])}
        self.assertEqual(rows["top"], counts(feedback=1, feedback_quoting=1, feedback_with_wc=1, quotes=5,
                                             excluded_cue=1, under_min_words=1, not_found=1, n=3, wc=1,
                                             prim_tight=3, wc_tight=1, n_short=2, n_long=1, wc_long=1))
        self.assertEqual(rows["middle"], counts(feedback=1))
        self.assertEqual(rows["bottom"], counts(feedback=1, feedback_quoting=1, quotes=1, n=1, prim_tight=1))
        rows2 = speceval.essay_rows("2", essays["2"])
        self.assertEqual(rows2[0]["rank"], "top")
        self.assertEqual(rows2[0]["counts"], counts(feedback=1, feedback_quoting=1, feedback_with_wc=1, quotes=1,
                                                    n=1, wc=1, prim_tight=1, wc_tight=1))


class AnalyseTest(unittest.TestCase):
    def rows(self, essays: int, top_wc: int, bottom_wc: int) -> list:
        out = []
        for i in range(essays):
            e = "E%04d" % i
            out.append({"essay": e, "set": "1", "rank": "top",
                        "counts": counts(feedback=1, n=2, wc=top_wc, n_short=1, wc_short=1)})
            out.append({"essay": e, "set": "4", "rank": "bottom",
                        "counts": counts(feedback=1, n=2, wc=bottom_wc, n_long=1)})
        return out

    def test_verdicts(self):
        res = speceval.analyse(self.rows(150, 1, 0), reps=200)
        self.assertEqual(res["essays"], 150)
        self.assertAlmostEqual(res["pooled"]["word_changed_rate"], 0.25)
        self.assertEqual(res["tests"]["E1_pooled_word_changed"]["verdict"], "did not hold")
        self.assertEqual(res["tests"]["E2_short_vs_long"]["verdict"], "held (short quotes higher)")
        self.assertAlmostEqual(res["tests"]["E3_top_vs_bottom"]["diff"], 0.5)
        self.assertTrue(res["tests"]["E3_top_vs_bottom"]["verdict"].startswith("held"))
        self.assertIsNone(res["by_rank"]["middle"]["word_changed_rate"])
        self.assertEqual(res["by_set"]["4"]["counts"]["n"], 300)

    def test_top_more_faithful(self):
        res = speceval.analyse(self.rows(150, 0, 1), reps=200)
        self.assertAlmostEqual(res["tests"]["E3_top_vs_bottom"]["diff"], -0.5)
        self.assertTrue(res["tests"]["E3_top_vs_bottom"]["verdict"].startswith("did not hold"))

    def test_margin(self):
        self.assertTrue(speceval.verdict_margin((-0.008, -0.002), 500, 500, 100).startswith("held"))
        self.assertEqual(speceval.verdict_margin((-0.03, 0.01), 500, 500, 100), "inconclusive")
        self.assertTrue(speceval.verdict_margin((-0.03, 0.01), 50, 500, 100).startswith("underpowered"))

    def test_underpowered(self):
        res = speceval.analyse(self.rows(20, 1, 0), reps=50)
        for name in ("E1_pooled_word_changed", "E2_short_vs_long", "E3_top_vs_bottom"):
            self.assertTrue(res["tests"][name]["verdict"].startswith("underpowered"), name)


class EndToEndTest(unittest.TestCase):
    def test_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = os.path.join(tmp, "speceval_dataset.json")
            with open(data, "w", encoding="utf-8") as fh:
                json.dump(records(), fh)
            out = os.path.join(tmp, "speceval.json")
            self.assertEqual(speceval.main(["--data", tmp, "--out", out, "--reps", "20",
                                            "--plan", os.path.join(tmp, "none.md")]), 0)
            with open(out, encoding="utf-8") as fh:
                res = json.load(fh)
        self.assertEqual(res["records"], 4)
        self.assertEqual(res["skipped_records"], 1)
        self.assertEqual(res["feedback_texts"], 4)
        self.assertEqual(res["essays"], 2)
        self.assertEqual(res["pooled"]["counts"]["n"], 5)
        self.assertEqual(res["pooled"]["counts"]["wc"], 2)
        self.assertEqual(res["by_rank"]["top"]["counts"]["n"], 4)
        self.assertEqual(res["by_rank"]["bottom"]["counts"]["n"], 1)
        self.assertFalse(res["sha256_as_probed"])
        self.assertNotIn("plan_sha256", res)
        text = json.dumps(res)
        for phrase in ("summer job", "quiet spaces", "library", "bridge"):
            self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
