# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Unit tests for audit8b.py (PLAN-8b.md). Synthetic data only; no network, no dataset."""
import argparse
import csv
import io
import json
import os
import tarfile
import tempfile
import unittest

import audit8b

HEADER = ["student_id", "lab", "submission_timestamp", "exp_group", "test_name", "ai_feedback_type",
          "ai_feedback_text", "source_file", "function_name", "code_snippet"]


def make_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(HEADER)
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def make_tar(path, members):
    with tarfile.open(path, "w:gz") as tf:
        for name, text in members:
            data = text.encode("utf-8")
            info = tarfile.TarInfo("progFeed-x/" + name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))


class SimilarityTests(unittest.TestCase):
    def test_tokens(self):
        self.assertEqual(audit8b.tokens("if n%2==0:"), ["if", "n", "%", "2", "=", "=", "0", ":"])
        self.assertEqual(audit8b.tokens(None), [])

    def test_exact_window(self):
        self.assertEqual(audit8b.best_similarity("x = 1", "y = 2\nx = 1\n"), 1.0)

    def test_near_copy(self):
        sim = audit8b.best_similarity("total = total + num", "total = total + n\n")
        self.assertAlmostEqual(sim, 8 / 9)
        self.assertEqual(audit8b.band(sim), "near")

    def test_no_overlap_and_empty(self):
        self.assertEqual(audit8b.best_similarity("while n > 0", "for i in range(3)"), 0.0)
        self.assertEqual(audit8b.best_similarity("", "x"), 0.0)
        self.assertEqual(audit8b.best_similarity("x", ""), 0.0)

    def test_band(self):
        b = audit8b.band
        self.assertEqual([b(1.0), b(0.8), b(0.79), b(0.5), b(0.49)], ["near", "near", "partial", "partial", "new"])


class SubmissionTests(unittest.TestCase):
    def test_ts_key(self):
        self.assertEqual(sorted(["ts10", "ts9", "ts2"], key=audit8b.ts_key), ["ts2", "ts9", "ts10"])
        self.assertLess(audit8b.ts_key("2025-02-03 9:00:00"), audit8b.ts_key("2025-02-03 14:05:09"))

    def test_submissions(self):
        by_folder = {"all_labs/lab05/s1/ts2/": ["all_labs/lab05/s1/ts2/f.py"],
                     "all_labs/lab05/s1/ts1/": ["all_labs/lab05/s1/ts1/f.py"],
                     "all_labs/lab05/s2/ts1/": ["all_labs/lab05/s2/ts1/f.py"]}
        self.assertEqual(audit8b.submissions(by_folder),
                         {("lab05", "s1"): ["ts1", "ts2"], ("lab05", "s2"): ["ts1"]})


class JudgeTests(unittest.TestCase):
    def test_diff_verdict(self):
        v = audit8b.diff_verdict
        self.assertEqual(v((1.0, 5.0), 30, 20), "held")
        self.assertEqual(v((-5.0, -1.0), 30, 20), "reversed")
        self.assertEqual(v((-1.0, 5.0), 30, 20), "no clear difference")
        self.assertEqual(v((1.0, 5.0), 10, 20), "underpowered")
        self.assertEqual(v(None, 30, 20), "underpowered")

    def test_judge_powered(self):
        recs = [{"student": "s%d" % (i % 10), "lab": "lab05", "status": "unsourced", "tokens": 3, "sim": 0.9,
                 "band": "near" if i % 4 else "new", "in_final": i % 2 == 0, "control": 0.1}
                for i in range(40)]
        q1, q2 = audit8b.judge(recs, reps=1000)
        self.assertEqual((q1["num"], q1["den"], q1["students"]), (30, 40, 10))
        self.assertEqual(q1["rate_pct"], 75.0)
        self.assertEqual(q1["verdict"], "holds")
        self.assertEqual((q2["den"], q2["recipient_in_final"]), (40, 20))
        self.assertEqual(q2["control_mean_pct"], 10.0)
        self.assertEqual(q2["mean_diff_pts"], 40.0)
        self.assertEqual(q2["verdict"], "held")


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tar = os.path.join(self.tmp.name, "progfeed.tar.gz")
        csv_text = make_csv([
            ["s1", "lab05", "ts1", "2", "test_a", "nl",
             "Your line `total = total + num` and `while n > 0:` and `x = 1`.", "f.py", "f", "def f(n): pass"],
            ["s4", "lab05", "ts1", "2", "test_a", "nl", "Try `y = 2 * n`.", "f.py", "f", ""],
        ])
        make_tar(self.tar, [
            ("all_submissions_consolidated.csv", csv_text),
            ("all_labs/lab05/s1/ts1/f.py", "def f(n):\n    total = total + n\n    x = 1\n"),
            ("all_labs/lab05/s1/ts2/f.py", "def f(n):\n    while n > 0:\n        n -= 1\n    x = 1\n"),
            ("all_labs/lab05/s2/ts1/f.py", "def f(n):\n    return n\n"),
            ("all_labs/lab05/s3/ts5/f.py", "def f(n):\n    while n > 0:\n        pass\n"),
            ("all_labs/lab05/s4/ts1/f.py", "def f(n):\n    return n\n"),
            ("autograders/lab05_autograder_x/f_desc.txt", "DESC"),
        ])

    def test_run(self):
        out = os.path.join(self.tmp.name, "out.json")
        md = os.path.join(self.tmp.name, "out.md")
        audit8b.run(argparse.Namespace(tar=self.tar, out=out, md=md, reps=20))
        with open(out, encoding="utf-8") as f:
            dump = f.read()
        rep = json.loads(dump)
        self.assertEqual(rep["dataset"]["nl_units"], 2)
        u = rep["code_spans"]["unsourced"]
        self.assertEqual((u["spans"], u["students"], u["median_tokens"]), (3, 2, 5))
        self.assertEqual(u["bands"], {"near": 1, "partial": 0, "new": 2})
        self.assertEqual((u["with_later_final"], u["in_final"], u["with_control"]), (2, 1, 2))
        self.assertEqual(u["control_mean_pct"], 16.67)
        self.assertEqual(u["in_final_by_band"], {"near": [0, 1], "partial": [0, 0], "new": [1, 1]})
        e = rep["code_spans"]["exact"]
        self.assertEqual((e["spans"], e["with_later_final"], e["in_final"], e["median_tokens"]), (1, 1, 1, 3))
        self.assertEqual(rep["code_spans"]["ws"]["spans"], 0)
        self.assertEqual(rep["code_spans"]["context"]["bands"], {"near": 0, "partial": 0, "new": 0})
        self.assertEqual(rep["per_lab"]["lab05"]["unsourced"], 3)
        q1, q2 = rep["predictions"]
        self.assertEqual((q1["num"], q1["den"], q1["rate_pct"], q1["verdict"]), (1, 3, 33.33, "underpowered"))
        self.assertEqual((q2["den"], q2["recipient_in_final"], q2["mean_diff_pts"], q2["verdict"]),
                         (2, 1, 33.33, "underpowered"))
        for secret in ("total = ", "while n", "y = 2", '"s1"', '"s4"', "DESC"):
            self.assertNotIn(secret, dump)
        with open(md, encoding="utf-8") as f:
            self.assertIn("| Q1 |", f.read())


if __name__ == "__main__":
    unittest.main()
