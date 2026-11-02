# PLAN-8b: the code snippets in classroom hints that are not in the student's file

Preregistered 2026-11-02 by MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0
(`audit8b.py`, `test_audit8b.py`), text CC BY 4.0.

## Why

Audit 8 ([`RESULTS-8.md`](RESULTS-8.md)) found that in ProgFeed, a real introductory Python course, 37 of the
177 backtick code snippets in gpt-4o-mini's natural-language hints (20.9%) are neither in the student's
submitted file nor in the problem text or prompt, although the prompt said "Do not suggest code changes". Audit
8 could not say what they are. Two questions matter for a student reading the hint:

- Is the snippet the student's own line with something changed (a misquote, or a quietly corrected line), or
  code the student never wrote?
- Does the snippet then turn up in the student's code? If hint code that breaks the "no code" rule ends up in
  later submissions, the rule is leaking in practice.

## What is known before this plan

Audit 8's published counts only: 343 hints to 119 students; 177 code spans (88 exact, 32 spacing only, 20 from
the problem text or prompt, 37 found nowhere); 34 of the 116 hints with code spans hold an unsourced one; the
per-lab counts in RESULTS-8.md. Nobody has read any hint text, code, or snippet, and nothing about similarity
or later submissions has been computed.

## Data

ProgFeed, github.com/umass-ml4ed/progFeed-dataset-public at commit `e020c7c013187dba7b4130991eadc539d115526a`
(CC BY 4.0; Heickal and Lan, arXiv:2606.08807), archive SHA-256 `084fe8f3070436eef8646f452f69fef2fc7430974dfd2e47e909814faf77e234`
(the one audit 8 used; the job stops on any other).

## Method

`audit8b.py` imports `audit8.py` and stops unless its SHA-256 (LF) is
`3a95bc68e2c2f4e52d1b958c6e2a8a0568f9b1cc093b9ce0c7ec1ce7342b75b9`, the file audit 8 ran. It reuses audit 8's
units, span extraction and code-span classes unchanged, so the 37 unsourced spans are audit 8's.

- **Similarity.** Each span and the student's submitted file are split into tokens (words and single
  punctuation marks). The span's similarity is the highest `difflib` ratio between its tokens and any run of
  the file's tokens that is one shorter, the same length or one longer. Bands: **near** (at least 0.8: the
  student's code with a small change), **partial** (0.5 to under 0.8), **new** (under 0.5: code the student did
  not write).
- **Final submission.** A student's submissions of a lab are ordered by the numbers in their timestamps. The
  recipient's final submission is the last one, and counts only if it is later than the hinted submission.
  The snippet is "in" a file if it is there as written or once all spacing is removed (audit 8's rule). The
  file is the one with the hinted file's name, else all files of that submission.
- **Control.** For each unsourced span with a later final submission: the share of the *other* students in the
  same lab whose final submission contains it. This asks whether the snippet is just code everyone ends up
  writing.

## Predictions

95% CIs come from 10,000 bootstrap resamples of students (seed 20261102), as in audit 8.

| id | prediction | verdict rule | floor |
|---|---|---|---|
| Q1 | More than 50% of unsourced code spans are **near** copies of the student's code | holds if the whole CI is above 50%, fails if wholly below, else inconclusive | 30 spans |
| Q2 | Unsourced spans appear in the recipient's final submission more often than in other students' final submissions (mean of recipient 0/1 minus the control share, in points) | held if the whole CI is above 0, reversed if below, else no clear difference | 20 spans |

Why these: the hint is about the student's own code and the prompt forbids suggesting code, so we expect
most unsourced snippets to be near-copies of a student line. If a hint shows code, we expect some students to
use it.

## Reported without a verdict

Similarity bands of the 20 spans from the problem text or prompt; for every code-span class, the median
length in tokens, how many have a later final submission and how many of those still (or newly) contain the
span; recipient uptake by similarity band; the mean control share; per-lab bands.

## Limits, stated in advance

- 37 spans from at most 34 hints: the intervals will be wide, and a verdict may well be inconclusive.
- A **near** snippet may be a misquote or a corrected line; tokens alone cannot tell which. A **new** snippet may
  be an idea written in code rather than a code suggestion.
- A final submission reflects much more than one hint (other hints, office hours, the autograder). Q2's control
  removes code that every student writes, not every other cause. Other students may have had their own hints.
- One model, one course, one prompt, five labs. Only counts are published: no code, no hint text, no ids.

## Procedure

One sealed CPU job (`audit8b-progfeed-v1`) waits until this file, `audit8b.py`, `test_audit8b.py` and
`audit8.py` are on the repository's main branch, downloads the archive at the pinned commit and checks its
SHA-256, runs the unit tests, then `python audit8b.py run`. Its output `audit8b-progfeed.json` records the
SHA-256 of this plan and both scripts. Results go in RESULTS-8b.md whatever they show.
