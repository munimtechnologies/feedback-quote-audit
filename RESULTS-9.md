# RESULTS-9: when a math tutor restates the student's work, is it what the student said?

Results of the preregistered audit 9 ([PLAN-9.md](PLAN-9.md)). Made with AI agents working in MV2's name
(MV2 of Munim, Inc.). Text CC BY 4.0, code Apache-2.0. Counts only: MRBench v3 is CC BY-SA 4.0, and no
dialogue text, reply text or ids are published.

The sealed job `audit9-mrbench-v1` ran on 2026-11-02 from 17:15:53 to 17:18:24 UTC. Its setup log shows it
fetched PLAN-9.md, `audit9.py` and `test_audit9.py` from this repository's main branch before it downloaded the
two pinned MRBench v3 files, and both SHA-256 values matched the ones in the plan. The unit tests passed, then
the audit ran. Full output: [`groundwork/audit-9/audit9-mrbench.json`](groundwork/audit-9/audit9-mrbench.json).

## Verdicts (verbatim from the job)

| id | prediction | n | observed | 95% CI | verdict |
|---|---|---|---|---|---|
| R1 | restatement sentences with no number from any student turn (context or nowhere), all tutors, dev + test | 244 | 10.66% (26/244); threshold 5.0% | [6.41, 15.35] | **held** |
| R2 | restatement sentences whose numbers are nowhere in the dialogue, all tutors, dev + test | 244 | 2.05% (5/244); threshold 2.0% | [0.41, 4.02] | **inconclusive** |
| R3 | unsourced share higher in replies labelled Mistake_Location 'No' or 'To some extent' (a) than 'Yes' (b), dev set | 160 | 18.18% (8/44) vs 13.79% (16/116), diff 4.39 pts | [-8.02, 17.82] | **no clear difference** |

Strict sentences by class: 218 student, 0 equivalent, 21 context (the number is only in the problem), 5 nowhere.

## What this means

- **About 1 in 9 restatements does not restate the student.** Of the 244 sentences in which a tutor says
  "you said / you calculated / your answer ..." with a number, 26 (10.7%) contain no number the student wrote.
  Most of these (21) name a number from the problem text instead; 5 name a number found nowhere in the dialogue.
  The rule is lenient (one shared number makes a sentence count as faithful), so 10.7% is a floor on how often
  the restated number is not the student's own, not an estimate of it.
- **Numbers from nowhere are rare, and 244 sentences are too few to say whether they are above 2%** (R2).
- **The dataset's own "did the tutor locate the mistake?" labels do not clearly track this** (R3). The
  difference points the predicted way (18.2% vs 13.8%) but the interval is wide. The labels judge each reply as
  a whole, not the restatement sentence, which weakens this test.

## Descriptive (no verdicts)

- Broad cues ("you have", "your result" ...): 264 sentences, 14.4% unsourced (often the tutor's own working).
- Dev set, LLM tutors vs the human tutors (Expert and Novice): 12.9% (18/139) vs 28.6% (6/21) unsourced. With
  only 21 human sentences this is not a comparison, and Expert tutors often restate the problem on purpose.
- Per tutor (strict, dev set): Llama 3.1 405B 3.9% of 51, Llama 3.1 8B 7.7% of 39, Sonnet 21.7% of 23,
  Mistral 33.3% of 15, Expert 25.0% of 20; others have 7 or fewer sentences. Eight of the nine anonymous test-set
  tutors have 0-10% unsourced on 7-13 sentences each; the ninth has a single sentence, and it is unsourced.
- Quoted spans: 232; 133 are "wrappers" (a reply set inside quotation marks; 79 of them Mistral's).

## Limits

All the limits stated in PLAN-9 apply: heuristic cues and sentence splitting; a tutor may restate a value the
student implied but did not write (only fractions, percents and number words are matched as equivalent); the
dialogues stop at the mistake; MRBench replies were written or generated for a benchmark, not sent to students.

## This closes the audit series

Audit 9 is the last audit in this repository. From 17 November 2026, MV2's education research moves to a
larger open question in learning science:
[munimtechnologies/learning-rate-regularity](https://github.com/munimtechnologies/learning-rate-regularity),
which asks whether the reported finding that students learn at "astonishingly" similar rates holds up once the
learning-curve model is allowed to be wrong. PREDICTIONS.md stays as last updated (audits 1-8b); audit 9's three
verdicts are recorded here.

— MV2, Munim, Inc., mv2@munimtech.com
