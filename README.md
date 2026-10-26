# feedback-quote-audit

Does AI feedback that has already been *published* quote the student's words exactly?

When writing feedback quotes a student's sentence, the quote should be what the student wrote. If a
model quietly fixes a spelling or a verb form while copying, the student never sees their own error.
MV2's preregistered studies in [feedback-commons](https://github.com/munimtechnologies/feedback-commons)
measured this for small local models generating feedback themselves (about 93% of matched quotes exact
in v5). This repository audits public datasets of AI-written essay feedback instead, starting with a
large model's.

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0; text CC BY 4.0.

## Audit 1: GLM-4.7 feedback on IELTS essays (preregistered, running)

- Data: [`Jackrong/IELTS-writing-feedback-reasoning`](https://huggingface.co/datasets/Jackrong/IELTS-writing-feedback-reasoning)
  (about 8,900 IELTS Writing Task 2 essays with Markdown feedback and reasoning text from GLM-4.7),
  pinned to revision `326db2de39a2da62b4f25c0fad80b10c844c56df`.
- Plan, hypotheses and verdict rules: [`PREREG.md`](PREREG.md), committed before any quote was checked.
- Results: `RESULTS.md`, added when the sealed run finishes. Only counts are published, never essay or
  feedback text (the essays' upstream dataset lists no licence).

## How it works

`audit.py` finds every passage the feedback puts in double quotation marks, sets aside quotes of the
exam question and suggested rewrites, and checks the rest against the essay with
`verbatim_quote_check.py` (a copy of feedback-commons `tools/verbatim_quote_check.py`; the sealed run
downloads it fresh from tag v0.8.0 and records its SHA-256 in the results; the same checker runs in the
offline [quote-check](https://github.com/munimtechnologies/quote-check) page). Each quote is
exact, same words (only punctuation, spacing or capitals differ), changed words, or not found.

```bash
python -m unittest -v
python audit.py --data glm47_final.jsonl --out results.json --workers 3
```

Python 3.10+, standard library only.

## Limits

Only double-quoted passages are checked; the rule that sets aside suggested rewrites is a heuristic;
one model, one exam, one dataset. See PREREG.md.

## Licence

Apache-2.0 (see LICENSE). By MV2 of Munim, Inc., mv2@munimtech.com.
