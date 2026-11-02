# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Munim, Inc. (MV2). Made with AI agents working in MV2's name.
"""Unit tests for probe9.py (synthetic data only)."""
import json
import os
import tempfile
import unittest

import probe9

ANN_A = {"Mistake_Identification": "Yes", "Mistake_Location": "No", "Providing_Guidance": "To some extent",
         "Actionability": "Yes"}
ANN_B = {"Mistake_Identification": "No", "Mistake_Location": "No", "Providing_Guidance": "No",
         "Actionability": "Maybe"}
RECS = [
    {"conversation_id": "1", "conversation_history": "Tutor: Solve it\nStudent: The answer is 12",
     "tutor_responses": {
         "GPT4": {"response": 'You said "the answer is 12". Check again.', "annotation": ANN_A},
         "Expert": {"response": "Let's look at step one.", "annotation": ANN_B}}},
    {"conversation_id": "2", "conversation_history": "Tutor: Hi", "tutor_responses": {}},
]


class TestProbe9(unittest.TestCase):
    def test_turns(self):
        h = "Tutor: Hi\nStudent: I got 12\nmore text\ntutor: ok\nStudent: 15"
        self.assertEqual(probe9.turns(h), [("Tutor", "Hi"), ("Student", "I got 12\nmore text"),
                                           ("Tutor", "ok"), ("Student", "15")])

    def test_quote_spans(self):
        t = 'You wrote "12 apples" and ' + chr(0x201C) + "then 15" + chr(0x201D) + "."
        self.assertEqual(probe9.quote_spans(t), ["12 apples", "then 15"])

    def test_band(self):
        self.assertEqual([probe9.band(n) for n in (0, 1, 2, 3, 4, 6, 7, 30)],
                         ["0", "1", "2-3", "2-3", "4-6", "4-6", "7+", "7+"])

    def test_cue_number_hits(self):
        t = ("You said 45. That is close! Your answer has no number here.\nYou" + chr(0x2019)
             + "ve got 3 left")
        self.assertEqual(probe9.cue_number_hits(t), ["you said", "you've"])

    def test_probe(self):
        r = probe9.probe(RECS)
        self.assertEqual(r["conversations"], 2)
        self.assertEqual(r["no_student_turn"], 1)
        self.assertEqual(r["student_last_turn_with_number"], 1)
        self.assertEqual(r["responses"], 2)
        g = r["per_tutor"]["GPT4"]
        self.assertEqual((g["with_quote"], g["quotes"], g["quote_words"]["4-6"]), (1, 1, 1))
        self.assertEqual((g["with_number"], g["with_cue_number"]), (1, 1))
        e = r["per_tutor"]["Expert"]
        self.assertEqual((e["with_quote"], e["with_number"], e["with_cue_number"]), (0, 0, 0))
        self.assertEqual(e["labels"]["Actionability"]["other"], 1)
        a = r["all"]
        self.assertEqual(a["labels"]["Mistake_Identification"], {"Yes": 1, "To some extent": 0, "No": 1,
                                                                 "other": 0})
        self.assertEqual(a["labels"]["Providing_Guidance"]["To some extent"], 1)
        self.assertEqual(r["cue_number_sentences"], {"you said": 1})

    def test_run_writes_counts_only(self):
        with tempfile.TemporaryDirectory() as d:
            data = os.path.join(d, "dev.json")
            out = os.path.join(d, "probe9.json")
            with open(data, "w", encoding="utf-8") as f:
                json.dump(RECS, f)
            with open(os.path.join(d, "odd.json"), "w", encoding="utf-8") as f:
                json.dump({"x": 1}, f)
            probe9.main(["--data", data, os.path.join(d, "odd.json"), "--out", out])
            with open(out, encoding="utf-8") as f:
                rep = json.load(f)
            self.assertEqual(rep["files"]["dev.json"]["conversations"], 2)
            self.assertEqual(len(rep["files"]["dev.json"]["sha256"]), 64)
            self.assertIn("error", rep["files"]["odd.json"])
            text = json.dumps(rep)
            self.assertNotIn("Check again", text)
            self.assertNotIn("Solve it", text)


if __name__ == "__main__":
    unittest.main()
