# Plan 2b: why do stronger essays get more changed quotes in GLM-4.7's feedback?

feedback-quote-audit, audit 2b. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-28, after the results of audits 1, 1b and 2 and before this pass ran. The sealed
run's setup refuses to start until this file is public in the repository. Apache-2.0 (code), CC BY 4.0 (text).

## Why

Audit 2 ([RESULTS-2.md](RESULTS-2.md)) found a surprise. In GLM-4.7's published IELTS feedback, essays
at band 7.0 or above get their words changed in quotes *more* often than essays at band 5.5 or below,
even with quote length held fixed (length-standardised word-changed rate 6.16% vs 3.61%; the opposite of
what the plan expected). Audit 2 read no quotes, so it could not say why. Its write-up listed three
explanations it had **not** tested. This pass tests those three, on the same data and with the same code,
using only aggregate counts. It is exploratory and the predictions are informed by audit 2, not blind.

The three explanations, from RESULTS-2.md:

1. **Suggested phrasing.** Feedback on strong essays may put recommended phrasing in quotation marks more
   often. A short "quote" of a phrase the essay only partly contains would be counted as changed.
2. **Rewrite cues.** Feedback on weak essays may mark its corrections with a rewrite cue more often, which
   takes those quotes out of the primary set, leaving the weak band's primary set cleaner.
3. **Near-miss matches.** A short phrase may be matched against a near-miss passage in the essay that the
   feedback was not actually quoting.

## What was already seen before this plan

Everything in RESULTS.md, RESULTS-1b.md, RESULTS-2.md and their JSON, including:

- The reversed band gap in the word-changed rate (6.16% vs 3.61% length-standardised; 6.05% vs 3.61% raw).
- Changes are concentrated in short (4-6-word) quotes: 6.09% of them change words, vs 1.50% of 26+-word
  quotes, and 71% of unmarked changes sit in 4-6-word quotes.
- The two band groups give about the same number of quotes per essay (5.4), so the gap is a rate, not a count.
- Audit 1's reversed exact-rate gap (+11.0 points, low minus high) survives holding length fixed.

No breakdown by rewrite-cue exclusion, by match similarity, or of the looseness of changed quotes, has been
computed or seen for the two band groups.

## Data and code

The same pinned file as audits 1, 1b and 2 (`glm47_final.jsonl`, SHA-256 `3b5eea94...69494`), the same
checker (feedback-commons v0.8.0), audit 1's `audit.py` (commit `0d1c75a`) and 1b's `explain.py` (commit
`d298ed9`). Both are imported, not copied, and hash-checked in setup. Only the feedback field
(`evaluation`). The pass must reproduce the earlier totals: 50,742 primary-set quotes and 20,520 / 2,712
quotes in the low / high band groups. If it does not, that is reported first.

Two groups, audit 1's: **weak** = band 5.5 or below, **strong** = band 7.0 or above. A quote is "matched"
if `verbatim_quote_check` finds it exact, punctuation/whitespace-only, or altered (word-level similarity of
the best-matching span at least 0.6). "Eligible" means matched and at least 4 words, before the rewrite-cue
and question filters. "Primary" is eligible and not rewrite-cued and not a quote of the exam question.
"Changed" (word-changed) is 1b's class. "Tight" means the best match has similarity 0.8 or above.

## Method (fixed)

For each test the statistic is the weak-band rate minus the strong-band rate. Its 95% CI is a percentile
bootstrap over essays, resampling the two groups independently, 10,000 resamples, seed
`feedback-quote-audit-2b-20261028`.

- **T1 (rewrite cues).** Rate = rewrite-cue-excluded quotes / eligible quotes.
- **T2 (similarity robustness).** Rate = changed quotes / primary quotes, both restricted to tight matches
  (similarity >= 0.8). The denominator therefore holds all exact and punctuation-only quotes plus the
  altered quotes whose match is tight.
- **T3 (loose matches).** Rate = changed quotes whose match is loose (similarity below 0.8) / all changed
  quotes.

## Predictions (verdict on the 95% CI of "weak band minus strong band")

- **T1 held** if the CI is above zero: the weak band excludes more quotes as rewrite-cued. This would make
  the weak band's primary set cleaner and is a mechanism that could produce audit 2's reversal.
- **T2 held** if the CI is below zero: the strong band still changes words more often even once only tight,
  genuine quote attempts are kept. This would mean the reversal is not merely loose or suggested phrasing.
- **T3 held** if the CI is below zero: the strong band's changed quotes are a loose match of the essay more
  often, the signature of suggested or near-miss phrasing counted as a change.

"Reversed" if the CI lies wholly on the other side of zero, otherwise "no clear difference". A test is
"underpowered" if either band group has fewer than 100 quotes in that test's denominator.

T2 and T3 adjudicate between the explanations. If T3 holds and T2 reverses or shows no clear difference, the
reversal was loose or suggested phrasing (explanations 1 and 3). If T2 holds, at least part of the reversal
is strong-band quotes that genuinely change the student's words. T1 tests whether differential rewrite-cue
exclusion (explanation 2) contributes.

## Also reported, with no prediction

- **R0:** the raw (not length-standardised) word-changed rate by band, so this pass's groups can be checked
  against audit 2's B2.
- The per-group counts behind every rate.

## Limits known in advance

- Similarity is `verbatim_quote_check`'s word-level best-match ratio, a proxy for "was this really quoted
  from the essay". It cannot by itself separate a suggested phrase from a real misquote; only a human
  reading of a sample could.
- These are rates, not a reading of any quote. This pass reads no quote text.
- The predictions are informed by audits 1, 1b and 2. They are not blind to the dataset.
- Band is the dataset's label, not a new rating. One model, one exam genre, one dataset.
- 1b's classes inherit 1b's limits: elision read generously, bold taken as a marked correction.

## Outputs

`band.json`: aggregate counts and rates only, with no essay or feedback text. No review sample is drawn.
