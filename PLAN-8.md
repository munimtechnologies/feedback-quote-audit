# PLAN-8: Do classroom programming hints quote the student's code faithfully?

Preregistered 2026-11-01 by MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0
(`audit8.py`, `test_audit8.py`), text CC BY 4.0.

Audits 1 to 7 asked whether AI feedback on student **essays** quotes the student's words exactly. Audit 8
asks the same question about AI hints on student **code** in a real course, using a dataset nobody has
checked this way.

## Data (fixed before any hint was read)

- **ProgFeed**, github.com/umass-ml4ed/progFeed-dataset-public at commit
  `e020c7c013187dba7b4130991eadc539d115526a` (CC BY 4.0). Heickal and Lan, "A Classroom Study of
  LLM-Generated Feedback Intervention in Introductory Programming", arXiv:2606.08807. 6,693 submissions from
  215 consenting students in an introductory Python course. Failing submissions got, at random, a
  natural-language hint (`nl`), an AI-written failing test case (`tc`) or nothing.
- The hints came from gpt-4o-mini. Its prompt held the problem description, the student's **whole submitted
  file**, a template (`openaiprompt_nlh.txt`) that says "Do not suggest code changes. Do not give test
  cases. Focus on one important issue.", and the function name (per the repo's `feedback_generation.py`).
- Before writing this plan we read only the README, `DATA_DICTIONARY.md`, the paper's abstract and method
  text, and a summary of one lab's `feedback_generation.py` and prompt template. We have not seen any hint
  text, any student code or any count from the table.

## Units and measures

- **Hint** = one distinct delivered `ai_feedback_text` for one (student, lab, submission, source file,
  function) in `all_submissions_consolidated.csv`, with `ai_feedback_type == "nl"`. Rows repeating the same
  text for several tests of the same function count once.
- **Reference text** = the submitted file `all_labs/<lab>/<student>/<timestamp>/<source_file>`. If it is
  missing we use the one file with that base name in the submission folder, else all files in the folder,
  else the row's `code_snippet`. How often each happens is reported.
- **Context** = the lab's `*_desc.txt` and `openaiprompt*` files plus the function name.
- **Spans** = each inline backtick span, plus each non-empty stripped line of a fenced code block.
  - *literal*: a number, a quoted string, True/False/None (reported, not judged);
  - *name*: an identifier, a dotted name, or either followed by `()`;
  - *code*: everything else, and every fenced line.
- A **code span** is `exact` if it is a substring of the file, `ws` if it matches once all whitespace is
  removed, `context` if it is in the context instead, else `unsourced`. "Found" = exact or ws.
- A **name span** is `file` (whole word in the file), `context`, `known` (every dotted part is in the file
  or context, or is a Python keyword, builtin or method of a built-in type), else `unsourced`.

## Predictions (nl hints only)

Rates are pooled over hints/spans; 95% CIs come from 10,000 bootstrap resamples of **students** (seed
20261101). A prediction **holds** if the whole CI is on the predicted side of the threshold, **fails** if it
is wholly on the other side, and is **inconclusive** otherwise. Below the floor it is **underpowered**.

| id | prediction | floor |
|---|---|---|
| P1 | more than 50% of hints contain at least one span | 200 hints |
| P2 | more than 70% of code spans are found in the student's file | 150 code spans |
| P3 | more than 90% of found code spans match exactly | 150 found code spans |
| P4 | fewer than 10% of name spans are unsourced | 150 name spans |
| P5 | fewer than 30% of hints with code spans hold an unsourced code span | 100 hints |

Why these: our essay audits found about 94-96% of AI quotes keep the student's words. Code is easier to
copy, but the prompt forbids suggesting code, so an unsourced code span is either a misquote or a broken
rule; we expect few of either. The thresholds are our guesses, written down before looking.

## Exploratory (no verdicts)

Per-lab totals, the share of hints with a fenced block, literal spans, block lines on their own, and the
same counts for the `tc` arm.

## Limits, stated in advance

- The test is literal. An unsourced span may be a fair paraphrase, a corrected line (which the prompt
  forbids), or text the dataset's scrubbing removed from the file. We count, we do not label intent.
- `known` names are generous: a name that only exists in Python passes even if the student never used it.
- One model, one course, one prompt. Students are clusters; labs differ.
- Only counts are published: no code, no hint text, no student ids.

## Procedure

One sealed CPU job (`audit8-progfeed-v1`) waits until this file, `audit8.py` and `test_audit8.py` are on
the repository's main branch, downloads the dataset archive at the pinned commit, runs the unit tests,
then `python audit8.py run`. Its output `audit8-progfeed.json` records the SHA-256 of this plan, the code,
the archive and the CSV. Results go in RESULTS-8.md as they come out, including any prediction that fails.
