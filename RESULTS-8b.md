# Follow-up 8b results: the hint code snippets that are not in the student's file often turn up in the student's final code

By MV2 of Munim, Inc. Made with AI agents working in his name. Text CC BY 4.0. Plan: [`PLAN-8b.md`](PLAN-8b.md)
(committed in 86bc54a before the job read any data). Code: `audit8b.py`, `test_audit8b.py` (it imports audit 8's
`audit8.py` unchanged; SHA-256 checked). Counts: [`audit8b-progfeed.json`](audit8b-progfeed.json). Only counts are
published: no code, no hint text, no student ids.

## The question

Audit 8 ([`RESULTS-8.md`](RESULTS-8.md)) found that in ProgFeed, a real introductory Python course, 37 of the 177
code snippets that gpt-4o-mini showed in backticks in its hints (20.9%) were neither in the student's submitted
file nor in the assignment text or prompt, although the prompt said "Do not suggest code changes." This follow-up
asks what those 37 snippets are:

- **Q1.** Are most of them near-copies of the student's own code (token similarity at least 0.8: the student's
  line with a small change)?
- **Q2.** Do they turn up in the recipient's final submission of the lab more often than in other students' final
  submissions of the same lab?

## Verdicts

37 unsourced snippets in hints to 28 students; all 37 had a later final submission and a control. 95% CIs from
10,000 bootstrap resamples of students (seed 20261102).

| ID | Prediction | Observed | 95% CI | Verdict |
|---|---|---|---|---|
| Q1 | More than 50% of unsourced code snippets are near-copies of the student's code | 40.5% (15 / 37) | 25.6-56.1% | **inconclusive** |
| Q2 | Unsourced snippets appear in the recipient's final submission more often than in other students' final submissions | recipient 48.6% (18 / 37) vs others 29.7% (mean); difference +18.9 pts | +5.5 to +34.5 pts | **held** |

## What the counts show

- **What the snippets are (Q1).** 15 of the 37 (40.5%) are near-copies of a stretch of the student's file
  (similarity at least 0.8), 15 (40.5%) are partial matches (0.5 to under 0.8), and 7 (18.9%) look like code the
  student did not write (under 0.5). Our guess that most would be near-copies is not supported: the point
  estimate is below 50% and the interval reaches both sides. The median snippet is 6 tokens long.
- **Where they go (Q2).** In 18 of the 37 cases the recipient's final submission of that lab contains the
  snippet as written or once spacing is ignored. Among the other students in the same lab, on average 29.7%
  of final submissions contain the same snippet, so a good part of it is code many students end up writing.
  The recipient's rate is higher by 18.9 points (CI +5.5 to +34.5).
- **By band, recipient uptake** (no verdict): near 6 of 15, partial 8 of 15, new 4 of 7. The excess is not
  confined to the near-copies, which are the ones most like code the student already had.
- **For comparison, the snippets that were the student's code** (no verdict): of the 83 snippets quoted exactly
  from the file and followed by a later final submission, 44 (53%) are still in the final submission, so about
  half of the lines a hint quotes are changed or gone by the end. For spacing-only matches it is 19 of 31. The
  20 snippets taken from the assignment text or prompt are almost never in the final code (1 of 20).
- So a snippet the hint showed but the student had not written ended up in the student's final code about as
  often (49%) as the student's own quoted line survived (53%).
- **Per lab** (unsourced snippets; near / partial / new): lab03 16 (5 / 6 / 5), lab05 6 (3 / 2 / 1), lab06 4
  (0 / 4 / 0), lab07 4 (4 / 0 / 0), lab09 7 (3 / 1 / 3).

## What Q2 does and does not show

Q2 held, but it is not proof that students copied code from the hints. The recipient's final submission grows
out of the recipient's own earlier code, so it can share more with a snippet built from that code than other
students' files do, hint or no hint; the control removes code that everyone writes, not this. Students also got
other hints, AI-written tests, office hours and autograder output. What Q2 does show is that the "no code"
instruction did not keep code out of the hints, and that code shown in a hint and absent from the student's file
often ends up in that student's final submission. Whether the hint caused it would need the dataset's randomised
arms (students who got no hint on the same problem), which this follow-up did not plan.

## Data and checks

- ProgFeed ([umass-ml4ed/progFeed-dataset-public](https://github.com/umass-ml4ed/progFeed-dataset-public) at
  commit `e020c7c0`, CC BY 4.0; Heickal and Lan, arXiv:2606.08807), archive SHA-256 `084fe8f3...e234`, the same
  one audit 8 used; 343 natural-language hints.
- The sealed job waited until the plan and both scripts were on main, downloaded the archive at the pinned
  commit, checked its SHA-256, ran the unit tests, then ran the follow-up in 1.7 seconds. It recorded the SHA-256
  of the plan (`cddf6de6...`), `audit8b.py` (`5bed8909...`) and `audit8.py` (`3a95bc68...`, the file audit 8 ran).

## Limits

- 37 snippets from 28 students: the intervals are wide.
- Similarity is a token proxy. A near-copy may be a misquote or a corrected line; a "new" snippet may be an idea
  written as code. No one read the snippets.
- "Contains" is literal (as written, or with all spacing removed); a student who used the idea with other names
  is not counted.
- One model, one course, one prompt, five labs; lab03 holds 16 of the 37.

## What it means in practice

If a programming hint is meant to point rather than give code, check what it actually shows. In this course,
1 in 5 snippets in the hints was not the student's code, and about half of those ended up in that student's
final submission. For a teacher, that is a reason to read the code in hints, not just the prose; for a tool
builder, a reason to check hint snippets against the student's file before sending them.

-- MV2, Munim, Inc., mv2@munimtech.com
