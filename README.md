# feedback-quote-audit

When AI feedback has already been *published*, does it quote the student's words exactly?

When feedback quotes a student's sentence, the quote should be what the student wrote. If a model quietly
fixes a spelling or a verb form while copying, the student never sees their own error.
MV2's preregistered studies in [feedback-commons](https://github.com/munimtechnologies/feedback-commons)
measured this for small local models generating feedback themselves (about 93% of matched quotes exact
in v5). This repository audits public datasets of AI-written essay feedback instead, starting with
feedback from a large model.

By MV2 of Munim, Inc. Made with AI agents working in his name. Code Apache-2.0; text CC BY 4.0.

## Audit 1: GLM-4.7 feedback on IELTS essays (preregistered, done)

- Data: [`Jackrong/IELTS-writing-feedback-reasoning`](https://huggingface.co/datasets/Jackrong/IELTS-writing-feedback-reasoning),
  pinned to revision `326db2de39a2da62b4f25c0fad80b10c844c56df`. It holds 8,946 IELTS Writing Task 2
  essays with Markdown feedback and reasoning text from GLM-4.7.
- Plan: [`PREREG.md`](PREREG.md), committed before any quote was checked.
- **Results: [`RESULTS.md`](RESULTS.md)** (`results.json` has the counts). The primary set has 50,742
  quotes. 37.7% of them are character-exact copies of the essay, so H1 (at least 95%) did not hold.
  92.3% keep the student's words and 7.7% change words. H2 and H3 came out reversed.
- Only counts are published, never essay or feedback text. The essays' upstream dataset lists no licence.

## Follow-up 1b: where the gap comes from (exploratory, planned before running, done)

- Plan: [`PLAN-1b.md`](PLAN-1b.md). Code: `explain.py`.
- **Results: [`RESULTS-1b.md`](RESULTS-1b.md)** (`explain.json` has the counts). All five predictions
  held.
- Once Markdown formatting and "..." are allowed for, 95.7% of quotes keep the student's words. The low
  exact rate was mostly formatting: 47.5% of quotes differ only in punctuation or quote marks at their two
  ends.
- 4.3% change the student's words. A third of those show the change in bold, so 2.8% of all quotes
  change the words without marking it.
- Audit 1's H3 reversal (reasoning vs feedback) disappears after the same normalisation.

## How it works

`audit.py` finds every passage the feedback puts in double quotation marks. It sets aside quotes of the
exam question and suggested rewrites, then checks the rest against the essay with
`verbatim_quote_check.py`. That file is a copy of feedback-commons `tools/verbatim_quote_check.py`; the
sealed run downloads it fresh from tag v0.8.0 and records its SHA-256 in the results. The same checker runs
in the offline [quote-check](https://github.com/munimtechnologies/quote-check) page. Each quote is exact,
same words (only punctuation, spacing or capitals differ), changed words, or not found. `explain.py` takes
the same quotes and records the first formatting step after which each one matches the essay.

```bash
sh setup.sh
python -m unittest -v
python audit.py --data glm47_final.jsonl --out results.json --workers 3
python explain.py --data glm47_final.jsonl --out explain.json --workers 3
```

Python 3.10+, standard library only.

## Limits

Only double-quoted passages are checked. The rule that sets aside suggested rewrites is a heuristic, and
it misses rewrites marked with bold inside the quote. The audit covers one model, one exam and one dataset.
See PREREG.md, RESULTS.md, PLAN-1b.md and RESULTS-1b.md.

## Licence

Apache-2.0 (see LICENSE). By MV2 of Munim, Inc., mv2@munimtech.com.
