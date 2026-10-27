# Results, follow-up 1b: why are most of GLM-4.7's quotes not character-exact?

feedback-quote-audit, follow-up to audit 1. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-27 from the sealed run's `explain.json` (in this repository). Text CC BY 4.0.

**In one line:** once Markdown formatting and "..." are allowed for, 95.7% of the passages GLM-4.7's
published IELTS feedback puts in quotation marks keep the student's words. Audit 1's low exact rate (37.7%)
was mostly formatting: almost half of all quotes (47.5%) differ from the essay only in punctuation or quote
marks at their two ends. 4.3% change the student's words. A third of those show the change in bold, and
2.8% of all quotes change the words without marking it. All five predictions in the plan held.

## What was run

- Plan: [PLAN-1b.md](PLAN-1b.md), committed at 2026-10-26 15:26:20 UTC (commit `d298ed9`), after audit 1's
  results and before this pass. The plan states what had already been seen: audit 1's totals and its
  30-quote reading. So this pass is exploratory, and its predictions are not blind tests. The sealed run
  started at 2026-10-27 06:23:48 UTC. `explain.json` records the SHA-256 of the plan it ran with
  (`ead5ad5f...`).
- Same data, code and quotes as audit 1: `glm47_final.jsonl` (SHA-256 `3b5eea94...69494`), checker
  feedback-commons v0.8.0 (`d53b6b46...`), and audit 1's `audit.py` at commit `0d1c75a`, imported rather
  than copied (`028c0d8d...`). The pass reproduced audit 1's totals exactly: 50,742 primary-set quotes in
  the feedback, 19,148 of them exact (`consistent_with_audit1: true`, for both fields).
- Python 3.12.15, CPU only, 24 minutes. Unit tests passed in the sealed container before the run. 95% CIs
  come from a bootstrap over essays (10,000 resamples) and cover the feedback (`evaluation`) only. The
  `reasoning` numbers are descriptive.
- Only counts are published. No essay or feedback text appears here or in `explain.json`.

## Where each quote first matches the essay (feedback, 50,742 quotes)

Steps are cumulative and run in the fixed order of the plan. Each quote is counted at the first step after
which it is found in the essay.

| step | quotes | share | matched so far |
|---|---:|---:|---:|
| exact (as audit 1) | 19,148 | 37.7% | 37.7% |
| Markdown emphasis removed | 823 | 1.6% | 39.4% |
| curly quotes and dashes made plain | 50 | 0.1% | 39.5% |
| spacing around punctuation made uniform | 1,437 | 2.8% | 42.3% |
| **punctuation, quote marks or "..." at the quote's two ends dropped** | **24,083** | **47.5%** | **89.8%** |
| capitals ignored | 1,194 | 2.4% | 92.1% |
| an inner "..." read as words left out | 1,726 | 3.4% | 95.5% |

Of the 2,281 quotes still unmatched, 85 differ only in other punctuation (for example an added hyphen), and
3 match word for word across an ellipsis. The other **2,193 (4.3%) change the student's words**:

| | quotes | share of all |
|---|---:|---:|
| change marked with Markdown emphasis inside the quote | 759 | 1.5% |
| change not marked | 1,434 | 2.8% |
| ...of which also leave words out with "..." | 84 | 0.2% |
| ...of which have no ellipsis (kinds below) | 1,350 | 2.7% |

Change kinds in those 1,350 unmarked quotes with no ellipsis, compared with audit 1's closest essay passage.
A quote can have several kinds: a word added or dropped 85.1%, a word swapped 24.7%, a one-for-one change of
spelling or form 6.8%, and a count of negation words that differs 2.2%.

Audit 1 called 3,918 quotes "changed words". Elision explains 1,715 of them (43.8%), and 10 match after a
formatting step. The remaining 2,193 are the word-changed quotes above.

## Predictions, exactly as planned (feedback field; verdict on the point estimate)

- **P1 held.** After formatting steps 1-5, 92.1% of quotes match (95% CI 91.9% to 92.3%). Threshold: at
  least 80%.
- **P2 held.** Elision explains 43.8% of audit 1's changed-words quotes (42.2% to 45.4%). Range: 30-70%.
- **P3 held.** Once elision is allowed, 4.3% of quotes change the student's words (4.1% to 4.5%). Threshold:
  at most 5.0%.
- **P4 held.** 34.6% of those word-changed quotes are marked with Markdown emphasis (32.5% to 36.8%).
  Threshold: at least 20%.
- **P5 held.** Unmarked word changes are 2.8% of quotes (2.7% to 3.0%). Range: 1.0-4.0%. Audit 1's 30-quote
  reading had guessed roughly 2%.

## The model's reasoning text (descriptive, 109,676 quotes)

In audit 1, the reasoning quoted exactly far more often than the final feedback (64.8% vs 37.7%; H3
reversed). After the same steps the two are almost level: 95.65% of reasoning quotes match after elision,
against 95.50% of feedback quotes. The word-faithful rates are 95.8% and 95.7%. The gap in audit 1 came
mostly from the quote ends: feedback quotes needed the edges step 47.5% of the time and reasoning quotes
17.0% of the time. Inner "..." is more common in the reasoning (8.1% vs 3.4% of quotes), which is why its
same-words rate in audit 1 was lower (87.7%). Reasoning quotes change words without marking it a little more
often (4.1% vs 2.8%). That difference has no CI, so we draw no conclusion from it.

## What the 30-quote review sample shows (words only, no text)

A random sample of 30 unmarked word-changed quotes with no ellipsis was read next to audit 1's closest essay
passage. The reader was one of the AI agents working in MV2's name, not a human teacher. Roughly:

- **About 6 silently fix the student's own error**: a misspelt word, a wrong verb form, or a wrong word
  choice. This is the case that matters most to a learner, because the quote hides the mistake the
  feedback is about.
- About 7 add, drop or swap a word inside an otherwise copied passage, without fixing an error. Examples
  are an intensifier added to the student's stance, an adjective dropped, or a different modal verb.
- About 5 are whole sentences rewritten into a better version, shown in quotation marks with no cue.
  These are suggested rewrites that the cue rule did not catch.
- About 6 are short stock phrases, such as a common linking phrase, of which the essay has only part. They
  look like suggested phrasing rather than quotes.
- About 6 copy the passage but add one word at its start or end.
- The automatic "negation" flag fired on 2 of the 30. On reading, neither reverses what the student said, so
  the 2.2% negation share is an upper bound on quotes that flip the student's meaning.

On this reading, about a fifth of the unmarked changes silently correct the student's error, or roughly
0.5% of all primary-set quotes, and about a third are rewrites or stock phrases rather than quotes. Both
estimates come from 30 quotes and have wide margins.

## What this means

- For Markdown feedback, the right headline is that 95.7% of GLM-4.7's quotes keep the student's words.
  The character-exact rate mostly measures how the model punctuates the ends of a quote.
- A quote checker for this kind of feedback should ignore punctuation and quote marks at a quote's ends and
  Markdown emphasis, read an inner "..." as words left out, and flag bold inside a quote as a marked edit,
  not a misquote. That leaves about 3 quotes in 100 that change the student's words unmarked, and those are
  the ones a teacher should look at.
- Audit 1's H3 reversal was a formatting effect. H2 (band) was not broken down here. Audit 2 will test
  whether it survives this normalisation and quote length.

## Deviations from the plan

None in method, data or verdict rules. The plan said the review sample would be summarised here. Audit 1's
code and data were reused unchanged.

## Limits

- The steps run in a fixed order, so a quote that differs in two ways is counted at the later step.
- Elision is read generously: the pieces only have to appear in order, however far apart.
- Change kinds are read against audit 1's closest passage, which can be off by a word at the edges.
- Bold inside a quote is taken as marking a correction.
- This covers one model (GLM-4.7), one exam genre and one dataset. The review reading was done by an AI
  agent, not a human.

## Reproduce

```bash
sh setup.sh            # fetches the pinned checker (audit.py is in this repository)
python -m unittest -v
python explain.py --data glm47_final.jsonl --out explain.json --workers 3
```

Apache-2.0 (code), CC BY 4.0 (text). MV2, Munim, Inc., mv2@munimtech.com.
