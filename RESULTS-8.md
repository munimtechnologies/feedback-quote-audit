# Audit 8 results: classroom programming hints name the student's code faithfully, but 1 in 5 code snippets is not in it

By MV2 of Munim, Inc. Made with AI agents working in his name. Text CC BY 4.0. Plan: [`PLAN-8.md`](PLAN-8.md)
(committed in c170220 before any hint was read). Code: `audit8.py`, `test_audit8.py`. Counts:
[`audit8-progfeed.json`](audit8-progfeed.json). Only counts are published: no code, no hint text, no student ids.

## The question

Audits 1-7 asked whether AI feedback on student **essays** quotes the student's words exactly. Audit 8 asks the
same about AI hints on student **code** from a real course. The data is ProgFeed
([umass-ml4ed/progFeed-dataset-public](https://github.com/umass-ml4ed/progFeed-dataset-public) at commit
`e020c7c0`, CC BY 4.0; Heickal and Lan, "A Classroom Study of LLM-Generated Feedback Intervention in Introductory
Programming", arXiv:2606.08807). In an introductory Python course, failing submissions got, at random, a
natural-language hint written by gpt-4o-mini, an AI-written failing test case, or nothing. The hint prompt held
the problem description, the student's whole submitted file, and the line "Do not suggest code changes."

The audit pulled every backtick span out of each hint and looked for it in the student's submitted file:

- **name** spans (a variable or function name, like `total` or `is_prime()`);
- **code** spans (anything longer, like `if n % 2 == 0:`): **exact** (in the file as written), **ws** (in the
  file once spacing is ignored), **context** (in the problem text or prompt instead), or **unsourced** (found
  nowhere);
- **literal** spans (a number or a string), reported without a verdict.

## Verdicts (natural-language hints)

343 hints to 119 students (every hint's submitted file was found in the dataset). 95% CIs from 10,000 bootstrap
resamples of students.

| ID | Prediction | Observed | 95% CI | Verdict |
|---|---|---|---|---|
| P1 | More than 50% of hints contain at least one backtick span | 90.7% (311 / 343) | 87.6-93.5% | **held** |
| P2 | More than 70% of code spans are found in the student's file (exact or spacing only) | 67.8% (120 / 177) | 59.7-75.2% | **inconclusive** |
| P3 | More than 90% of found code spans match the file exactly | 73.3% (88 / 120) | - | **underpowered** (floor 150) |
| P4 | Fewer than 10% of name spans are found nowhere | 0.39% (2 / 519) | 0.0-1.0% | **held** |
| P5 | Fewer than 30% of hints with code spans hold a code span found nowhere | 29.3% (34 / 116) | 20.3-39.5% | **inconclusive** |

## What the counts show

- **Names are the student's own.** 505 of 519 name spans (97.3%) are in the student's file, 11 more are in the
  problem text, and only 2 are found nowhere.
- **Code snippets are another matter.** Of 177 code spans: 88 (49.7%) are in the file as written, 32 (18.1%)
  match only once spacing is ignored, 20 (11.3%) come from the problem text or prompt, and **37 (20.9%) are found
  nowhere**, neither in the student's file nor in what the model was shown. 34 of the 116 hints that show code
  (29.3%) contain at least one such snippet.
- The prompt said "Do not suggest code changes", so each unsourced snippet is one of three things: a misquote
  of the student's line, a piece of corrected or new code (which the prompt forbade), or an idea written in code
  form. This audit counts; it cannot tell which. Follow-up 8b is planned to measure how close each one is to
  a line the student wrote and whether it turns up in the student's next submission.
- **Spacing.** 32 of the 120 snippets that are in the file (26.7%) differ from it only in spacing (we did not
  check whether the spacing ever mattered, as Python indentation can). P3 needed 150 found snippets for a verdict and had 120.
- **Literals:** 33 of 40 are in the student's file, 1 in the problem text, 6 elsewhere.
- **No fenced code blocks.** None of the 343 hints contains a fenced code block; every snippet is inline.

## Exploratory (no verdicts)

Per lab (natural-language hints; code spans exact / ws / context / unsourced):

| lab | hints | students | hints with spans | code spans | name spans |
|---|---|---|---|---|---|
| lab03 | 171 | 76 | 161 | 34 / 22 / 1 / 16 | 235 |
| lab05 | 38 | 21 | 33 | 14 / 3 / 8 / 6 | 53 |
| lab06 | 35 | 19 | 34 | 3 / 0 / 0 / 4 | 98 |
| lab07 | 36 | 22 | 34 | 10 / 4 / 0 / 4 | 65 |
| lab09 | 63 | 22 | 49 | 27 / 3 / 11 / 7 | 68 |

Only five labs had natural-language hints in the table. The 1,083 AI-written failing test cases (156 students)
contain no backtick spans at all, so this method says nothing about them.

## Data and checks

- `all_submissions_consolidated.csv`: 17,385 rows (SHA-256 `228124c5...`); 343 natural-language and 1,083
  test-case feedback texts after removing rows that repeat the same text for several tests of one function.
  Archive SHA-256 `084fe8f3...`, 9,567 submission files.
- The job checked that the plan and code it ran are the ones on the repository's main branch (plan SHA-256
  `ca580531...`, `audit8.py` `3a95bc68...`), ran the unit tests, then ran the audit in 3 seconds.

## Limits

- The test is literal. An unsourced snippet may be a fair paraphrase, a corrected line, or text the dataset's
  anonymisation changed in the file. We count, we do not label intent.
- `known` names are generous (only 1 span needed it).
- One model (gpt-4o-mini), one course, one prompt, five labs; lab03 holds half the hints. Students are clusters.
- Code spans are few (177), so P2, P3 and P5 have wide intervals.
- No one read the hints or the code.

## What it means in practice

When an AI hint names a variable or function, it is almost always the student's own. When it shows a line of
code, check it against the student's file: in this course about 1 in 5 such snippets was not in the file or in
the assignment, even though the model was told not to suggest code. A student who reads "your line `...`"
should find that line before changing anything.

-- MV2, Munim, Inc., mv2@munimtech.com
