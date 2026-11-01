# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Unit tests for audit8.py (PLAN-8.md). Synthetic data only; no network, no dataset."""
import argparse
import csv
import io
import json
import os
import tarfile
import tempfile
import unittest

import audit8

HEADER = ["student_id", "lab", "submission_timestamp", "exp_group", "test_name", "ai_feedback_type",
          "ai_feedback_text", "source_file", "function_name", "code_snippet"]


def make_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(HEADER)
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def make_rec(spans=0, code=None, name=None, literal=None):
    rec = audit8.empty_rec()
    rec["spans"] = spans
    for key, vals in (("code", code), ("name", name), ("literal", literal)):
        for k, v in (vals or {}).items():
            rec[key][k] = v
    return rec


def make_tar(path, members):
    with tarfile.open(path, "w:gz") as tf:
        for name, text in members:
            data = text.encode("utf-8")
            info = tarfile.TarInfo("progFeed-x/" + name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))


class SpanTests(unittest.TestCase):
    def test_extract_inline_and_fenced(self):
        text = ("Look at `for i in range(n):` and `total`.\n```python\nx = 1\n\n  y = 2\n```\n"
                "Also ``skip`` here.")
        self.assertEqual(audit8.extract_spans(text), [
            ("block", "x = 1"), ("block", "y = 2"),
            ("inline", "for i in range(n):"), ("inline", "total")])

    def test_unclosed_fence_and_empty(self):
        self.assertEqual(audit8.extract_spans("```python\nx = 1"), [])
        self.assertEqual(audit8.extract_spans(None), [])
        self.assertEqual(audit8.extract_spans("a ` ` b"), [])

    def test_span_kind(self):
        k = audit8.span_kind
        self.assertEqual(k("inline", "42"), "literal")
        self.assertEqual(k("inline", "'abc'"), "literal")
        self.assertEqual(k("inline", "None"), "literal")
        self.assertEqual(k("inline", "total"), "name")
        self.assertEqual(k("inline", "is_prime()"), "name")
        self.assertEqual(k("inline", "lst.append"), "name")
        self.assertEqual(k("inline", '"a" + "b"'), "code")
        self.assertEqual(k("inline", "n % 2 == 0"), "code")
        self.assertEqual(k("block", "x"), "code")

    def test_code_status(self):
        f = "def f(n):\n    if n%2 == 0:\n        return True\n"
        ctx = "Write f(n) that returns sum(range(n))"
        fw, cw = audit8.nows(f), audit8.nows(ctx)
        cs = audit8.code_status
        self.assertEqual(cs("if n%2 == 0:", f, fw, ctx, cw), "exact")
        self.assertEqual(cs("if n % 2 == 0:", f, fw, ctx, cw), "ws")
        self.assertEqual(cs("sum(range(n))", f, fw, ctx, cw), "context")
        self.assertEqual(cs("while n > 0:", f, fw, ctx, cw), "unsourced")

    def test_name_status(self):
        f = "lst.append(x)\ntotal = 0\n"
        ctx = "count_strings"
        ns = audit8.name_status
        self.assertEqual(ns("append", f, ctx), "file")
        self.assertEqual(ns("total", f, ctx), "file")
        self.assertEqual(ns("count_strings()", f, ctx), "context")
        self.assertEqual(ns("len", f, ctx), "known")
        self.assertEqual(ns("str.lower", f, ctx), "known")
        self.assertEqual(ns("frobnicate", f, ctx), "unsourced")
        self.assertEqual(ns("lst.frob", f, ctx), "unsourced")
        self.assertEqual(ns("tot", f, ctx), "unsourced")

    def test_audit_unit(self):
        text = "Check `if n%2 == 0:` and `total` and `5`.\n```\nwhile n > 0:\n```"
        f = "def f(n):\n    total = 0\n    if n%2 == 0:\n        return 5\n"
        rec = audit8.audit_unit(text, f, "")
        self.assertEqual(rec["spans"], 4)
        self.assertEqual(rec["code"], {"exact": 1, "ws": 0, "context": 0, "unsourced": 1})
        self.assertEqual(rec["block"], {"exact": 0, "ws": 0, "context": 0, "unsourced": 1})
        self.assertEqual(rec["name"], {"file": 1, "context": 0, "known": 0, "unsourced": 0})
        self.assertEqual(rec["literal"], {"file": 1, "context": 0, "other": 0})
        self.assertTrue(rec["fenced"])


class CsvTests(unittest.TestCase):
    def rows(self):
        return [
            ["s1", "lab05", "t1", "2", "test_a", "nl", "Hint A", "f.py", "f", "def f():\n  pass"],
            ["s1", "lab05", "t1", "2", "test_b", "nl", "Hint A", "f.py", "f", "def f():\n  pass"],
            ["s1", "lab05", "t1", "2", "test_c", "nl", "", "f.py", "g", "def g():\n  pass"],
            ["s2", "lab05", "t2", "1", "test_a", "tc", "assert f() == 1", "f.py", "f", "def f():\n  return 0"],
            ["s2", "lab05", "t3", "2", "test_a", "nl", "Hint B\nline2", "f.py", "f", "def f():\n  return 2"],
        ]

    def test_read_units_nl(self):
        rows, typed, units = audit8.read_units(make_csv(self.rows()), "nl")
        self.assertEqual((rows, typed, len(units)), (5, 3, 2))
        self.assertEqual(units[0]["student"], "s1")
        self.assertEqual(units[1]["text"], "Hint B\nline2")
        self.assertEqual(units[1]["snippet"], "def f():\n  return 2")

    def test_read_units_tc(self):
        rows, typed, units = audit8.read_units(make_csv(self.rows()), "tc")
        self.assertEqual((rows, typed, len(units)), (5, 1, 1))

    def test_missing_column(self):
        with self.assertRaises(ValueError):
            audit8.read_units("a,b\n1,2\n", "nl")


class StatsTests(unittest.TestCase):
    def test_cluster_ci(self):
        self.assertEqual(audit8.cluster_ci([[1, 2], [1, 2], [1, 2], [0, 0]], reps=100), (50.0, 50.0))
        self.assertIsNone(audit8.cluster_ci([[0, 0]], reps=10))
        lo, hi = audit8.cluster_ci([[0, 1], [1, 1], [1, 1], [1, 1]], reps=500)
        self.assertTrue(0.0 <= lo <= 75.0 <= hi <= 100.0)
        self.assertEqual(audit8.cluster_ci([[0, 1], [1, 1]], reps=50), audit8.cluster_ci([[0, 1], [1, 1]], reps=50))

    def test_verdict(self):
        v = audit8.verdict
        self.assertEqual(v((60, 80), 100, 150, 50, ">"), "underpowered")
        self.assertEqual(v((60, 80), 200, 150, 50, ">"), "holds")
        self.assertEqual(v((30, 40), 200, 150, 50, ">"), "fails")
        self.assertEqual(v((40, 60), 200, 150, 50, ">"), "inconclusive")
        self.assertEqual(v((5, 8), 200, 150, 10, "<"), "holds")
        self.assertEqual(v((12, 15), 200, 150, 10, "<"), "fails")
        self.assertEqual(v(None, 200, 150, 10, "<"), "underpowered")

    def test_judge(self):
        rec = make_rec(spans=1, code={"exact": 1})
        recs = [("s%d" % (i % 30), "lab05", rec) for i in range(300)]
        res = {r["id"]: r for r in audit8.judge(recs, reps=50)}
        self.assertEqual(res["P1"]["verdict"], "holds")
        self.assertEqual(res["P1"]["den"], 300)
        self.assertEqual(res["P1"]["students"], 30)
        self.assertEqual(res["P2"]["rate_pct"], 100.0)
        self.assertEqual(res["P2"]["verdict"], "holds")
        self.assertEqual(res["P3"]["verdict"], "holds")
        self.assertEqual(res["P4"]["verdict"], "underpowered")
        self.assertIsNone(res["P4"]["rate_pct"])
        self.assertEqual(res["P5"]["rate_pct"], 0.0)
        self.assertEqual(res["P5"]["verdict"], "holds")

    def test_totals(self):
        recs = [("s1", "lab05", make_rec(spans=2, code={"exact": 1}, name={"file": 1})),
                ("s2", "lab06", make_rec())]
        t = audit8.totals(recs)
        self.assertEqual((t["hints"], t["students"], t["with_spans"], t["spans"]), (2, 2, 1, 2))
        self.assertEqual(t["code"]["exact"], 1)
        self.assertEqual(t["name"]["file"], 1)

    def test_lab_key(self):
        self.assertEqual(audit8.lab_key("pre-lab01"), audit8.lab_key("preLab01_autograder_github".split("_autograder")[0]))
        self.assertEqual(audit8.lab_key("lab05"), "lab05")


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tar = os.path.join(self.tmp.name, "progfeed.tar.gz")
        csv_text = make_csv([
            ["s1", "lab05", "ts1", "2", "test_a", "nl", "Look at `if n%2 == 0:` in `is_prime`.", "f.py", "is_prime",
             "def is_prime(n):\n    if n%2 == 0:\n        return False"],
        ])
        g = "autograders/lab05_autograder_github_ai_abc/"
        make_tar(self.tar, [
            ("all_submissions_consolidated.csv", csv_text),
            ("all_labs/lab05/s1/ts1/f.py", "def is_prime(n):\n    if n%2 == 0:\n        return False\n"),
            ("all_labs/lab05/s1/ts1/results.json", "{}"),
            (g + "is_prime_desc.txt", "PRIME DESC"),
            (g + "openaiprompt_nlh.txt", "PROMPT TEXT"),
            (g + "run_tests.py", "print(1)"),
            (g + "files.txt", "FILES LIST"),
        ])

    def test_read_tar_and_lookup(self):
        files = audit8.read_tar(self.tar)
        self.assertIn("all_submissions_consolidated.csv", files)
        self.assertIn("all_labs/lab05/s1/ts1/f.py", files)
        self.assertNotIn("all_labs/lab05/s1/ts1/results.json", files)
        self.assertNotIn("autograders/lab05_autograder_github_ai_abc/run_tests.py", files)
        ctx = audit8.contexts(files)
        self.assertEqual(list(ctx), ["lab05"])
        self.assertIn("PRIME DESC", ctx["lab05"])
        self.assertIn("PROMPT TEXT", ctx["lab05"])
        self.assertNotIn("FILES LIST", ctx["lab05"])
        by_folder = audit8.folders(files)
        self.assertEqual(by_folder, {"all_labs/lab05/s1/ts1/": ["all_labs/lab05/s1/ts1/f.py"]})
        unit = {"lab": "lab05", "student": "s1", "ts": "ts1", "source_file": "f.py", "snippet": "SNIP"}
        self.assertEqual(audit8.source_for(unit, files, by_folder)[0], "file")
        self.assertEqual(audit8.source_for(dict(unit, source_file="sub/f.py"), files, by_folder)[0], "file")
        self.assertEqual(audit8.source_for(dict(unit, source_file="g.py"), files, by_folder)[0], "folder")
        self.assertEqual(audit8.source_for(dict(unit, student="s9"), files, by_folder), ("snippet", "SNIP"))

    def test_run_end_to_end(self):
        out = os.path.join(self.tmp.name, "out.json")
        md = os.path.join(self.tmp.name, "out.md")
        audit8.run(argparse.Namespace(tar=self.tar, out=out, md=md, reps=20))
        with open(out, encoding="utf-8") as f:
            rep = json.load(f)
        self.assertEqual(rep["dataset"]["nl_units"], 1)
        self.assertEqual(rep["dataset"]["tc_units"], 0)
        self.assertEqual(rep["source_match"]["nl"], {"file": 1, "folder": 0, "snippet": 0})
        self.assertEqual(rep["totals"]["nl"]["code"]["exact"], 1)
        self.assertEqual(rep["totals"]["nl"]["name"]["file"], 1)
        self.assertEqual([p["verdict"] for p in rep["predictions"]], ["underpowered"] * 5)
        self.assertNotIn("is_prime", json.dumps(rep))
        with open(md, encoding="utf-8") as f:
            self.assertIn("| P1 |", f.read())


if __name__ == "__main__":
    unittest.main()
