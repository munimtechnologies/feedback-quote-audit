# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Unit tests for audit9.py (synthetic data only)."""
import json
import os
import tempfile
import unittest

import audit9


def ann(ml):
    return {"Mistake_Identification": "Yes", "Mistake_Location": ml, "Providing_Guidance": "Yes",
            "Actionability": "Yes"}


REC1 = {"conversation_id": "1",
        "conversation_history": "Tutor: The question is: Tom has 12 apples and buys 3 more.\n"
                                "Student: 12 + 3 = 16, so Tom has sixteen apples.",
        "tutor_responses": {
            "GPT4": {"response": "You said 16 apples. Let's check 12 + 3 again.", "annotation": ann("No")},
            "Llama318B": {"response": "You calculated 15 apples, which is right.", "annotation": ann("Yes")},
            "Expert": {"response": "In step 2, you added 12 and 4.", "annotation": ann("Yes")},
            "Mistral": {"response": 'If you added 12 and 4, you get 16. Your work says "12 + 3 = 16" here.',
                        "annotation": ann("Yes")}}}
REC2 = {"conversation_id": "2",
        "conversation_history": "Tutor: What is 7 x 8?\nStudent: It is 54.",
        "tutor_responses": {
            "Tutor_1": {"response": 'How did you get 45? You wrote "it is 54" which is close.'},
            "Tutor_2": {"response": '"Let us multiply 7 by 8 to get the product."'}}}
REC3 = {"conversation_id": "3",
        "conversation_history": "Tutor: Share 1 pizza.\nStudent: Each gets 1/2 of it, so 50% each.",
        "tutor_responses": {
            "Phi3": {"response": "You said 0.5 of the pizza.", "annotation": ann("To some extent")},
            "Sonnet": {"response": "You" + chr(0x2019) + "ve got 3 slices left.", "annotation": ann("No")},
            "Gemini": {"response": "Can you say 7 more?", "annotation": ann("No")},
            "Llama31405B": {"response": "You stated the 2nd step uses 3.", "annotation": ann("No")}}}
FILES = [("dev", [REC1, REC3]), ("test", [REC2])]


class TestHelpers(unittest.TestCase):
    def test_turns(self):
        h = "Tutor: Hi\nStudent: I got 12\nmore text\ntutor: ok\nStudent: 15"
        self.assertEqual(audit9.turns(h), [("Tutor", "Hi"), ("Student", "I got 12\nmore text"),
                                           ("Tutor", "ok"), ("Student", "15")])

    def test_canon(self):
        self.assertEqual([audit9.canon(s) for s in ("0.50", "10", "3.0", "000", "007", "2.25")],
                         ["0.5", "10", "3", "0", "7", "2.25"])

    def test_numbers_strip(self):
        t = "Step 3: you got 1,200.50 and 007 in the 2nd row"
        self.assertEqual(audit9.numbers(t, strip=True), ["1200.5", "7"])
        self.assertEqual(audit9.numbers(t), ["3", "1200.5", "7", "2"])

    def test_number_sets(self):
        c, v = audit9.number_sets(["Each gets 1/2 of it, so 50% each and five more"])
        self.assertEqual(c, {"1", "2", "50", "5"})
        self.assertTrue(audit9.close(0.5, v))
        self.assertTrue(audit9.close(5.0, v))
        self.assertFalse(audit9.close(3.0, v))

    def test_restatements(self):
        r = "If you added 4, it works. You got 12! Did you say 5? How did you get 9? Your total is 7."
        self.assertEqual(audit9.restatements(r), [("strict", ["12"]), ("strict", ["9"]), ("broad", ["7"])])
        self.assertEqual(audit9.restatements("You have calculated 8. Your answer of 3 is off."),
                         [("strict", ["8"]), ("strict", ["3"])])
        self.assertEqual(audit9.restatements("In step 2, you said it."), [])

    def test_quotes_and_class(self):
        ctx = audit9.context("Tutor: Read this.\nStudent: the cat sat on the mat")
        qs = audit9.quotes('You wrote "the cat sat" but also "a dog sat on the mat" and "x".')
        self.assertEqual([(q[0], q[1], q[2]) for q in qs],
                         [(["the", "cat", "sat"], False, True),
                          (["a", "dog", "sat", "on", "the", "mat"], False, True)])
        self.assertEqual(audit9.quote_class(qs[0][0], ctx), "student")
        self.assertEqual(audit9.quote_class(["read", "this"], ctx), "context")
        self.assertEqual(audit9.quote_class(["the", "cat", "sat", "on", "a", "mat"], ctx), "near")
        self.assertEqual(audit9.quote_class(["green", "eggs"], ctx), "nowhere")


class TestAnalyse(unittest.TestCase):
    def setUp(self):
        self.units, self.qunits = audit9.analyse(FILES)

    def test_units(self):
        strict = [(u["tutor"], u["cls"], u["ml"], u["human"]) for u in self.units if u["kind"] == "strict"]
        self.assertEqual(sorted(strict), sorted([
            ("dev/GPT4", "student", "No", False), ("dev/Llama318B", "nowhere", "Yes", False),
            ("dev/Expert", "student", "Yes", True), ("dev/Phi3", "equivalent", "To some extent", False),
            ("dev/Llama31405B", "nowhere", "No", False), ("test/Tutor_1", "nowhere", None, None),
            ("test/Tutor_1", "student", None, None)]))
        broad = sorted((u["tutor"], u["cls"]) for u in self.units if u["kind"] == "broad")
        self.assertEqual(broad, [("dev/Mistral", "student"), ("dev/Mistral", "student"), ("dev/Sonnet", "nowhere")])

    def test_judge_points(self):
        r1, r2, r3 = audit9.judge(self.units, reps=50)
        self.assertEqual((r1["num"], r1["den"], r1["dialogues"], r1["rate_pct"]), (3, 7, 3, 42.86))
        self.assertEqual((r2["num"], r2["den"], r2["rate_pct"]), (3, 7, 42.86))
        self.assertEqual((r1["verdict"], r1["ci95"]), ("underpowered", None))
        self.assertEqual((r3["a_num"], r3["a_den"], r3["b_num"], r3["b_den"]), (1, 3, 1, 2))
        self.assertEqual((r3["a_pct"], r3["b_pct"], r3["diff_pts"]), (33.33, 50.0, -16.67))
        self.assertEqual(r3["verdict"], "underpowered")

    def test_judge_small_floors(self):
        r1, _r2, r3 = audit9.judge(self.units, reps=200, floor_level=1, floor_side=1)
        self.assertIn(r1["verdict"], ("held", "did not hold", "inconclusive"))
        self.assertTrue(0 <= r1["ci95"][0] <= r1["ci95"][1] <= 100)
        self.assertIn(r3["verdict"], ("held", "reversed", "no clear difference"))

    def test_judge_degenerate(self):
        us = [{"dlg": d, "kind": "strict", "cls": "nowhere", "ml": None} for d in ("a", "b", "c")]
        r1, r2, r3 = audit9.judge(us, reps=50, floor_level=1, floor_side=1)
        self.assertEqual((r1["ci95"], r1["verdict"]), ([100.0, 100.0], "held"))
        self.assertEqual(r2["verdict"], "held")
        self.assertEqual((r3["a_den"], r3["b_den"], r3["diff_pts"], r3["verdict"]), (0, 0, None, "underpowered"))

    def test_verdicts(self):
        self.assertEqual(audit9.level_verdict((6.0, 9.0), 200, 150, 5.0), "held")
        self.assertEqual(audit9.level_verdict((1.0, 4.0), 200, 150, 5.0), "did not hold")
        self.assertEqual(audit9.level_verdict((4.0, 9.0), 200, 150, 5.0), "inconclusive")
        self.assertEqual(audit9.level_verdict((6.0, 9.0), 100, 150, 5.0), "underpowered")
        self.assertEqual(audit9.diff_verdict((1.0, 3.0), 40, 40, 30), "held")
        self.assertEqual(audit9.diff_verdict((-3.0, -1.0), 40, 40, 30), "reversed")
        self.assertEqual(audit9.diff_verdict((-3.0, 1.0), 40, 40, 30), "no clear difference")
        self.assertEqual(audit9.diff_verdict((1.0, 3.0), 40, 20, 30), "underpowered")

    def test_describe(self):
        d = audit9.describe(self.units, self.qunits, reps=50)
        self.assertEqual(d["strict"], {"student": 3, "equivalent": 1, "context": 0, "nowhere": 3, "n": 7,
                                       "unsourced_pct": 42.86})
        self.assertEqual((d["broad"]["n"], d["broad"]["unsourced_pct"]), (3, 33.33))
        self.assertEqual(d["per_tutor_strict"]["test/Tutor_1"]["unsourced_pct"], 50.0)
        lh = d["llm_vs_human_dev"]
        self.assertEqual((lh["a_num"], lh["a_den"], lh["b_num"], lh["b_den"], lh["diff_pts"]), (2, 4, 0, 1, 50.0))
        self.assertNotIn("verdict", lh)
        self.assertEqual([d["mistake_location_strict"][k]["n"] for k in ("Yes", "To some extent", "No")], [2, 1, 2])
        q = d["quotes"]
        self.assertEqual((q["spans"], q["wrappers"]), (3, 1))
        self.assertEqual((q["attributed"]["n"], q["attributed"]["student"], q["unattributed"]["n"]), (2, 2, 0))
        self.assertEqual(q["wrappers_per_tutor"], {"test/Tutor_2": 1})


class TestRun(unittest.TestCase):
    def test_run_counts_only_and_pin(self):
        with tempfile.TemporaryDirectory() as d:
            dev = os.path.join(d, "dev.json")
            test = os.path.join(d, "test.json")
            out = os.path.join(d, "a9.json")
            md = os.path.join(d, "a9.md")
            with open(dev, "w", encoding="utf-8") as f:
                json.dump([REC1, REC3], f)
            with open(test, "w", encoding="utf-8") as f:
                json.dump([REC2], f)
            with self.assertRaises(SystemExit):
                audit9.main(["run", "--data", dev, test, "--out", out])
            audit9.main(["run", "--data", dev, test, "--out", out, "--md", md, "--reps", "50",
                         "--allow-unpinned"])
            with open(out, encoding="utf-8") as f:
                text = f.read()
            with open(md, encoding="utf-8") as f:
                mdtext = f.read()
            rep = json.loads(text)
            self.assertFalse(rep["dataset"]["pinned"])
            self.assertEqual(rep["dataset"]["files"]["dev.json"]["records"], 2)
            self.assertEqual([p["id"] for p in rep["predictions"]], ["R1", "R2", "R3"])
            self.assertEqual(len(rep["audit9_sha256_lf"]), 64)
            for word in ("apples", "pizza", "Tom", "slices", "product"):
                self.assertNotIn(word, text)
                self.assertNotIn(word, mdtext)
            self.assertIn("| R1 |", mdtext)


if __name__ == "__main__":
    unittest.main()
