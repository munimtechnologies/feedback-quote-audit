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

## Audit 2: quote length and essay band (planned before running, done)

- Plan: [`PLAN-2.md`](PLAN-2.md). Code: `length.py` (`setup-2.sh` fetches the pinned code and waits until
  the plan is public).
- **Results: [`RESULTS-2.md`](RESULTS-2.md)** (`length.json` has the counts). All five predictions came out
  reversed.
- Short quotes change the student's words most often: 6.1% of 4-6-word quotes against 1.5% of quotes over
  25 words. 71% of the unmarked changes are in 4-6-word quotes, and each word in a long quote is also less
  likely to change.
- Essays at band 7.0 or above get more changed quotes than essays at 5.5 or below, even with quote length
  held fixed (4.1% vs 2.5% unmarked).
- Audit 1's band gap in the exact rate survives holding length fixed (+11.8 points). Most of it is
  formatting.

## Audit 2b: why do stronger essays get more changed quotes? (planned before running, done)

- Plan: [`PLAN-2b.md`](PLAN-2b.md). Code: `band.py` (`setup-2b.sh` fetches the pinned code and waits until
  the plan is public).
- **Results: [`RESULTS-2b.md`](RESULTS-2b.md)** (`band.json` has the counts). Audit 2's reversed band
  finding was a surprise, and audit 2 read no quotes, so it left three explanations untested. This pass
  tested them on the same data with counts only.
- The reversal has two causes. Weaker essays have more of their quotes marked as rewrites and taken out of
  the measured set (T1: 49.2% vs 42.6% of eligible quotes), which leaves their remaining set cleaner. But
  even among tight, genuine quote attempts (word-level similarity at least 0.8) the strong band still
  changes words more often (T2: 3.03% vs 1.69%).
- There is no clear band difference in how loose the changed quotes are (T3), so "suggested phrasing" does
  not explain the strong band's higher rate; loose near-misses are common in both bands.

## How it works

`audit.py` finds every passage the feedback puts in double quotation marks. It sets aside quotes of the
exam question and suggested rewrites, then checks the rest against the essay with
`verbatim_quote_check.py`. That file is a copy of feedback-commons `tools/verbatim_quote_check.py`; the
sealed run downloads it fresh from tag v0.8.0 and records its SHA-256 in the results. The same checker runs
in the offline [quote-check](https://github.com/munimtechnologies/quote-check) page. Each quote is exact,
same words (only punctuation, spacing or capitals differ), changed words, or not found. `explain.py` takes
the same quotes and records the first formatting step after which each one matches the essay. `length.py`
breaks 1b's classes down by quote length and essay band, and `band.py` breaks the band difference down by
rewrite-cue exclusion and by how tightly each quote matches the essay.

```bash
sh setup.sh
python -m unittest -v
python audit.py --data glm47_final.jsonl --out results.json --workers 3
python explain.py --data glm47_final.jsonl --out explain.json --workers 3
python length.py --data glm47_final.jsonl --out length.json --workers 3
python band.py --data glm47_final.jsonl --out band.json --workers 3
```

Python 3.10+, standard library only.

## Limits

Only double-quoted passages are checked. The rule that sets aside suggested rewrites is a heuristic, and
it misses rewrites marked with bold inside the quote. Short quotes have the least context to match on, so
some short "changed" quotes may be suggested phrasing rather than misquotes. The audit covers one model,
one exam and one dataset. See PREREG.md, RESULTS.md, PLAN-1b.md, RESULTS-1b.md, PLAN-2.md, RESULTS-2.md,
PLAN-2b.md and RESULTS-2b.md.

## Licence

Apache-2.0 (see LICENSE). By MV2 of Munim, Inc., mv2@munimtech.com.
