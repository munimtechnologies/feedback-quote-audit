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
"""Tests for feedtype.py (audit 4). Made-up essays and feedback only; no FeedType text."""
import io
import json
import os
import tarfile
import tempfile
import unittest

import feedtype

P0 = "My summer job taught me patience and careful planning every day."
P1 = "Working at the library showed me how quiet spaces help people think clearly."
TEACHER_NOTE = "Try to explain why quiet spaces matter for your readers here."
MODEL_COMMENT = "\n".join([
    'You open with "My summer job taught me patience" and it works.',            # exact, in paragraph
    'Later "how quiet spaces help people think" links back.',                    # exact, other paragraph
    'Here "My summer job taught me patience and careful plans every day" is unclear.',  # one word changed
    'Instead "My job made me patient and organised" reads well.',                 # rewrite cue
    'Your teacher asked you to "explain why quiet spaces matter for your readers" and that is fair.',
    'Also "summer job" is vague.',                                                # under four words
])


def doc() -> dict:
    return {"paragraphs": [
        {"body": P0, "annotations": [{"type": "model_feedback", "model_comment": MODEL_COMMENT,
                                      "model_category": "Mistakes"}]},
        {"body": P1, "annotations": [
            {"type": "note", "comment": TEACHER_NOTE, "teacher_category": "Elaboration",
             "context_left": "", "context_right": ""},
            {"type": "note", "comment": 'You say "how quiet spaces help people think" and that is good.',
             "teacher_category": "Praise", "context_left": "", "context_right": ""},
            {"type": "highlight", "color": "pink", "text": "library", "comment": "",
             "context_left": "", "context_right": ""},
            {"type": "model_feedback", "model_comment": "Good detail about the library.",
             "model_category": "Praise"}]},
    ]}


def counts(**kw) -> dict:
    c = dict.fromkeys(feedtype.KEYS, 0)
    c.update(kw)
    return c


class LocateTest(unittest.TestCase):
    def test_paths(self):
        root = "FeedType-%s/FeedType/" % feedtype.COMMIT
        self.assertEqual(feedtype.locate(root + "Models/Qwen70B/Prompt 2/Batch_1/Course_1/Class_1/E_ID0001.json"),
                         ("model", "Qwen70B", "Prompt 2", "E_ID0001"))
        self.assertEqual(feedtype.locate(root + "Teacher/Batch_2/Course_3/Class_1/E_ID0002.json"),
                         ("teacher", "Teacher", "", "E_ID0002"))
        self.assertIsNone(feedtype.locate(root + "Models/.DS_Store"))
        self.assertIsNone(feedtype.locate(root + "Models/Qwen70B/Prompt 2/Batch_1/._E_ID0001.json"))
        self.assertIsNone(feedtype.locate("FeedType-x/README.md"))
        self.assertIsNone(feedtype.locate(root + "Models/Qwen70B.json"))


class CountsTest(unittest.TestCase):
    def test_model_file(self):
        c = feedtype.file_counts(doc(), "model")
        self.assertEqual(c, counts(comments=2, comments_quoting=1, quotes=6, excluded_cue=1, excluded_teacher=1,
                                   under_min_words=1, not_found=2, n=3, wc=1, prim_tight=3, wc_tight=1,
                                   wc_loose=0, faithful=2, faithful_elsewhere=1, n_short=2, wc_short=0,
                                   n_long=1, wc_long=1))

    def test_teacher_file(self):
        c = feedtype.file_counts(doc(), "teacher")
        self.assertEqual(c, counts(comments=2, comments_quoting=1, quotes=1, n=1, prim_tight=1, faithful=1,
                                   n_short=1))

    def test_bad_json(self):
        out = feedtype.process(("model", "Qwen70B", "Prompt 1", "E", b"{not json"))
        self.assertTrue(out["error"])
        out = feedtype.process(("model", "Qwen70B", "Prompt 1", "E", b"[]"))
        self.assertEqual(out["counts"], counts())

    def test_in_paragraph_elision(self):
        self.assertTrue(feedtype.in_paragraph('"My summer job ... careful planning every day"', P0))
        self.assertFalse(feedtype.in_paragraph('"My summer job ... careful planning every day"', P1))


class AnalyseTest(unittest.TestCase):
    def results(self, drafts: int) -> list:
        out = []
        for i in range(drafts):
            d = "D%03d" % i
            out.append({"kind": "model", "model": "LLaMa8B", "prompt": "Prompt 1", "draft": d,
                        "counts": counts(n=2, wc=1, faithful=1, n_short=1, wc_short=1, comments=1)})
            out.append({"kind": "model", "model": "Qwen70B", "prompt": "Prompt 1", "draft": d,
                        "counts": counts(n=2, faithful=2, n_long=1, comments=1)})
        out.append({"kind": "teacher", "model": "Teacher", "prompt": "", "draft": "D000",
                    "counts": counts(n=1, faithful=1)})
        out.append({"kind": "model", "model": "Qwen70B", "prompt": "Prompt 1", "draft": "bad", "error": True})
        return out

    def test_verdicts(self):
        res = feedtype.analyse(self.results(150), reps=200)
        self.assertEqual(res["parse_errors"], 1)
        self.assertEqual(res["model_files"], 300)
        self.assertEqual(res["missing_models"], ["Mistral7B", "Mistral24B", "Gemini2Flash", "LearnLM"])
        self.assertAlmostEqual(res["pooled"]["word_changed_rate"], 0.25)
        self.assertEqual(res["tests"]["C1_pooled_word_changed"]["verdict"], "did not hold")
        self.assertEqual(res["tests"]["C2_small_vs_large"]["verdict"], "held (small models higher)")
        self.assertAlmostEqual(res["tests"]["C2_small_vs_large"]["diff"], 0.5)
        self.assertEqual(res["tests"]["C3_short_vs_long"]["verdict"], "held (short quotes higher)")
        self.assertEqual(res["by_model"]["Qwen70B"]["word_changed_rate"], 0.0)
        self.assertEqual(res["teacher"]["counts"]["n"], 1)
        self.assertIn("Qwen70B / Prompt 1", res["by_cell"])

    def test_underpowered(self):
        res = feedtype.analyse(self.results(20), reps=50)
        self.assertTrue(res["tests"]["C1_pooled_word_changed"]["verdict"].startswith("underpowered"))
        self.assertTrue(res["tests"]["C2_small_vs_large"]["verdict"].startswith("underpowered"))


class EndToEndTest(unittest.TestCase):
    def test_main(self):
        root = "FeedType-%s/FeedType/" % feedtype.COMMIT
        files = {root + "Models/LLaMa8B/Prompt 1/Batch_1/Course_1/Class_1/E_ID0001.json": doc(),
                 root + "Models/Qwen70B/Prompt 3/Batch_1/Course_1/Class_1/E_ID0001.json": doc(),
                 root + "Teacher/Batch_1/Course_1/Class_1/E_ID0001.json": doc()}
        with tempfile.TemporaryDirectory() as tmp:
            tar_path = os.path.join(tmp, "feedtype.tar.gz")
            with tarfile.open(tar_path, "w:gz") as tar:
                for name, d in list(files.items()) + [(root + "Models/.DS_Store", None)]:
                    data = b"x" if d is None else json.dumps(d).encode("utf-8")
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))
            out = os.path.join(tmp, "feedtype.json")
            self.assertEqual(feedtype.main(["--data", tmp, "--out", out, "--reps", "20",
                                            "--plan", os.path.join(tmp, "none.md")]), 0)
            with open(out, encoding="utf-8") as fh:
                res = json.load(fh)
        self.assertEqual(res["model_files"], 2)
        self.assertEqual(res["teacher_files"], 1)
        self.assertEqual(res["pooled"]["counts"]["n"], 6)
        self.assertEqual(res["pooled"]["counts"]["wc"], 2)
        self.assertTrue(res["commit_in_root"])
        self.assertEqual(res["by_model"]["LLaMa8B"]["elsewhere_share_of_faithful"], 0.5)
        self.assertNotIn("plan_sha256", res)
        text = json.dumps(res)
        for phrase in ("summer job", "quiet spaces", "library"):
            self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
