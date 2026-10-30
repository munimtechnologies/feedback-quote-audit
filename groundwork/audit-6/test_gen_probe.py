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
"""Tests for gen_probe and fetch on synthetic data (no model, no network)."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
import unittest

import fetch
import gen_probe as gp

ESSAY = ("Students should be allowed to use phones at lunch because it helps them relax. "
         "Many students feel stressed during the day, and a short break with friends online can help. "
         "However, phones must stay off in class so that everyone can focus on learning.")


def essay(i: int, ell: str, words: int = 200) -> dict:
    return {"id": "E%03d" % i, "ell": ell, "assignment": "Write about phones.",
            "text": " ".join(["word%d" % i] * words)}


class FakeLlm:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def create_chat_completion(self, **kw):
        self.calls.append(kw)
        content, finish = self.replies.pop(0)
        return {"choices": [{"message": {"content": content}, "finish_reason": finish}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50}}


class Classify(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(gp.classify("it helps them relax", ESSAY), "exact")

    def test_format_only(self):
        self.assertEqual(gp.classify(chr(0x201C) + "Many  students feel STRESSED during the day." + chr(0x201D), ESSAY),
                         "format_only")

    def test_ellipsis_join(self):
        self.assertEqual(gp.classify("Many students feel stressed ... phones must stay off in class", ESSAY),
                         "ellipsis_join")
        self.assertEqual(gp.classify("Many students feel stressed" + chr(0x2026) + "phones must stay off", ESSAY),
                         "ellipsis_join")

    def test_changed_near(self):
        self.assertEqual(gp.classify("many students feel very stressed during the day and a short break", ESSAY),
                         "changed_near")

    def test_changed_loose_and_not_found(self):
        self.assertEqual(gp.classify("phones should stay off in every class so students focus", ESSAY), "changed_loose")
        self.assertEqual(gp.classify("the electoral college should be abolished now", ESSAY), "not_found")

    def test_empty(self):
        self.assertEqual(gp.classify("   ", ESSAY), "empty")
        self.assertEqual(gp.classify("...", ESSAY), "empty")


class Parse(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(gp.parse('{"feedback": [{"excerpt": "a", "comment": "b"}, 3]}'),
                         [{"excerpt": "a", "comment": "b"}])
        self.assertIsNone(gp.parse('{"feedback": [{"excerpt": "a"'))
        self.assertIsNone(gp.parse('["x"]'))
        self.assertIsNone(gp.parse('{"items": []}'))


class Select(unittest.TestCase):
    def test_csv_one_record_per_essay(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "train.csv")
            with open(path, "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["essay_id_comp", "full_text", "ell_status", "assignment", "discourse_text"])
                w.writerow(["A1", ESSAY, "Yes", "Write.", "x"])
                w.writerow(["A1", ESSAY, "Yes", "Write.", "y"])
                w.writerow(["B2", "short essay", " ", "Write.", "z"])
            got = gp.essays_from_csv(path)
        self.assertEqual([e["id"] for e in got], ["A1", "B2"])
        self.assertEqual(got[1]["ell"], "")

    def test_pick_balanced_deterministic_and_windowed(self):
        pool = [essay(i, "Yes") for i in range(8)] + [essay(i, "No") for i in range(8, 16)]
        pool.append(essay(99, "Yes", words=50))  # too short
        pool.append(essay(98, "", words=200))  # no status
        a = gp.pick(pool, 3)
        b = gp.pick(list(reversed(pool)), 3)
        self.assertEqual([e["id"] for e in a], [e["id"] for e in b])
        self.assertEqual([e["ell"] for e in a], ["Yes"] * 3 + ["No"] * 3)
        self.assertNotIn("E099", [e["id"] for e in a])
        self.assertNotIn("E098", [e["id"] for e in a])

    def test_messages_label(self):
        e = essay(1, "No")
        base = gp.messages(e, "baseline")[1]["content"]
        ell = gp.messages(e, "ell")[1]["content"]
        self.assertTrue(ell.endswith(base))
        self.assertIn("English language learner", ell)
        self.assertNotIn("English language learner", base)


class RunAndReport(unittest.TestCase):
    def test_run_summarise_and_no_text_leaks(self):
        e = {"id": "SECRET-ID", "ell": "Yes", "assignment": "Write.", "text": ESSAY}
        good = json.dumps({"feedback": [{"excerpt": "it helps them relax", "comment": "Nice."},
                                        {"excerpt": "the electoral college", "comment": "Hmm."}]})
        llm = FakeLlm([(good, "stop"), ('{"feedback": [', "length")])
        rows = gp.run_model(llm, [e], ["baseline", "ell"], 300)
        self.assertEqual(len(llm.calls), 2)
        self.assertEqual(llm.calls[0]["response_format"]["schema"], gp.SCHEMA)
        self.assertEqual(rows[0]["categories"], {"exact": 1, "not_found": 1})
        self.assertEqual(rows[0]["excerpt_words"], [4, 3])
        self.assertFalse(rows[1]["parsed"])
        s = gp.summarise(rows)
        self.assertEqual(s["all"]["calls"], 2)
        self.assertEqual(s["all"]["parsed"], 1)
        self.assertEqual(s["all"]["truncated"], 1)
        self.assertEqual(s["baseline|ell=Yes"]["items"], 2)
        dumped = json.dumps({"rows": rows, "summary": s})
        for leak in ("SECRET-ID", "relax", "electoral", "Nice."):
            self.assertNotIn(leak, dumped)


class Fetch(unittest.TestCase):
    def test_ensure_cached_then_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "f.bin")
            want = hashlib.sha256(b"right").hexdigest()

            def bad(dest):
                with open(dest, "wb") as fh:
                    fh.write(b"wrong")

            def broken(dest):
                raise OSError("offline")

            def good(dest):
                with open(dest, "wb") as fh:
                    fh.write(b"right")

            self.assertEqual(fetch.ensure(path, want, [("broken", broken), ("bad", bad), ("good", good)]), "good")
            self.assertEqual(fetch.ensure(path, want, [("broken", broken)]), "cached")
            with self.assertRaises(SystemExit):
                fetch.ensure(os.path.join(d, "g.bin"), want, [("bad", bad)])

    def test_pick_dir_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            blocker = os.path.join(d, "file")
            with open(blocker, "w") as fh:
                fh.write("x")
            got = fetch.pick_dir([os.path.join(blocker, "sub"), os.path.join(d, "ok")])
        self.assertTrue(got.endswith("ok"))

    def test_models_pinned(self):
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "models.json"), encoding="utf-8") as fh:
            models = json.load(fh)
        for m in models:
            self.assertEqual(len(m["commit"]), 40)
            self.assertEqual(len(m["sha256"]), 64)
            self.assertEqual(m["license"], "apache-2.0")


if __name__ == "__main__":
    unittest.main()
