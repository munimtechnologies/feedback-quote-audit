# Results, audit 2: do longer quotes change the student's words more, and do weaker essays get more changed quotes?

feedback-quote-audit, audit 2. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-27 from the sealed run's `length.json` (in this repository). Text CC BY 4.0.

**In one line:** all five predictions came out **reversed**. In GLM-4.7's published IELTS feedback, the
*short* quotes change the student's words most often: 6.1% of 4-6-word quotes against 1.5% of quotes over
25 words, and 71% of all unmarked word changes sit in 4-6-word quotes. The *stronger* essays (band 7.0 or
above) get more changed quotes than the weaker ones (band 5.5 or below), even with quote length held fixed:
4.1% against 2.5% unmarked. Audit 1's band gap in the exact rate survives holding length fixed (+11.8
points). Most of it is formatting.

## What was run

- Plan: [PLAN-2.md](PLAN-2.md), committed at 2026-10-27 09:16:49 UTC (commit `eccdbea`), after audit 1 and
  follow-up 1b and before this pass. The sealed run's setup checked that the public plan was identical to
  the one it held before reading any data. It logged "PLAN-2.md is public and identical". The run started
  at 15:35:10 UTC, about 6 hours 18 minutes after the commit. `length.json` records the plan's SHA-256
  (`a6400f6c...`).
- Same data and code as audit 1 and 1b: `glm47_final.jsonl` (SHA-256 `3b5eea94...69494`), checker
  feedback-commons v0.8.0 (`d53b6b46...`), audit 1's `audit.py` at commit `0d1c75a` (`028c0d8d...`) and
  1b's `explain.py` at commit `d298ed9` (`9f2959da...`). All were imported, not copied, and hash-checked in
  setup.
- The pass reproduced every earlier total: 50,742 primary-set feedback quotes, 19,148 exact, 2,193
  word-changed, 1,434 unmarked word-changed, and 20,520 / 2,712 quotes in the low / high band groups
  (`consistent_with_earlier: true`).
- Python 3.12.15, CPU only, 13 minutes, peak memory 0.54 GB. Unit tests passed in the sealed container
  before the run. 95% CIs come from 10,000 bootstrap resamples over essays (seed
  `feedback-quote-audit-2-20261027`).
- Only counts are published. No essay or feedback text appears here or in `length.json`, and no review
  sample was drawn in this pass.

## By quote length (feedback, 50,742 quotes)

"Formatting only" means the quote matches after 1b's steps 1-5 (emphasis, curly quotes, spacing, the
quote's two ends, capitals). "Word-changed" is 1b's class: the quote still does not match after an inner
"..." is read as words left out. "Unmarked" means the change is not shown in bold or italics.

| words in quote | quotes | share | exact | formatting only | word-changed (95% CI) | unmarked (95% CI) | changed words per 100 quoted |
|---|---:|---:|---:|---:|---:|---:|---:|
| 4-6 | 22,413 | 44.2% | 38.1% | 51.8% | 6.09% (5.78-6.42) | 4.55% (4.27-4.83) | 1.99 |
| 7-10 | 14,636 | 28.8% | 21.7% | 70.7% | 3.65% (3.34-3.97) | 1.63% (1.42-1.85) | 1.18 |
| 11-15 | 5,890 | 11.6% | 34.7% | 58.7% | 2.68% (2.26-3.13) | 0.98% (0.74-1.25) | 0.90 |
| 16-25 | 4,800 | 9.5% | 67.8% | 28.8% | 1.90% (1.52-2.28) | 1.52% (1.19-1.87) | 0.75 |
| 26+ | 3,003 | 5.9% | 71.4% | 26.0% | 1.50% (1.10-1.93) | 1.47% (1.06-1.90) | 0.49 |

The counts behind the rates are as follows. Word-changed quotes per bin: 1,365 / 534 / 158 / 91 / 45 (total
2,193). Unmarked: 1,020 / 239 / 58 / 73 / 44 (total 1,434). The marked changes (bold inside the quote) are
therefore 345 / 295 / 100 / 18 / 1. Almost every change in a quote over 15 words is unmarked.

The exact rate is not monotone in length. It is lowest for 7-10-word quotes (21.7%), where 70.7% of quotes
differ only in formatting. Over 15 words it climbs to about 70%.

## Predictions, exactly as planned (verdict on the 95% CI of "26+ minus 4-6" or "low band minus high band")

- **L1 reversed.** Word-changed rate: 1.50% in 26+-word quotes vs 6.09% in 4-6-word quotes. Difference
  -4.59 points (95% CI -5.12 to -4.05, paired by essay).
- **L2 reversed.** Unmarked word-changed rate: 1.47% vs 4.55%. Difference -3.09 points (-3.59 to -2.58).
- **L3 reversed.** Changed words per 100 quoted words: 0.49 vs 1.99. Difference -1.50 (-1.71 to -1.28).
  So each word is also less likely to change in a long quote, not only each quote.
- **B1 reversed.** Length-standardised unmarked word-changed rate: 2.53% at band 5.5 or below (3,774
  essays) vs 4.10% at band 7.0 or above (500 essays). Difference -1.57 points (-2.41 to -0.78). Raw,
  unstandardised: 2.52% vs 4.02%.
- **B2 reversed.** Length-standardised word-changed rate: 3.61% vs 6.16%. Difference -2.55 points (-3.47
  to -1.65). Raw: 3.61% vs 6.05%.

No test was underpowered. The smallest length bin compared has 3,003 quotes (floor 300). The smallest band
stratum has 181 quotes (high band, 26+ words; floor 100). Standardisation weights, fixed from all quotes:
4-10 words 73.0%, 11-25 words 21.1%, 26+ words 5.9%.

## Also reported, with no prediction

- **B3, exact rate by band.** Length-standardised: 41.85% (low) vs 30.01% (high), +11.85 points (95% CI
  +9.90 to +13.75). Raw: +10.98, as in audit 1. Holding quote length fixed does not remove audit 1's band
  gap. It grows slightly.
- **B4, formatting-only rate by band.** Length-standardised: 51.60% vs 59.77%, -8.17 points (-10.24 to
  -6.12). Raw: -7.47.
- So, holding length fixed, the high band's 11.85-point lower exact rate splits into three parts. 8.17
  points are quotes that differ only in formatting, 2.55 points are quotes that change words, and about
  1.1 points are the remaining classes (inner "...", other punctuation). The two band groups give about
  the same number of quotes per essay (5.4).

## What this means

- **Look at short quotes first.** Changes to the student's words are concentrated in 4-6-word quotes,
  which are 44% of all quotes but hold 62% of word-changed quotes and 71% of the unmarked ones. Long quotes
  are mostly faithful: once formatting is set aside, 97.4% of 26+-word quotes match. Our expectation came
  from two 30-quote readings, where the whole-sentence rewrites stood out. It was the wrong way round.
- **Weaker essays do not get more silently changed quotes.** The plan reasoned that weaker essays have more
  errors to fix silently, so their quotes would change more often. At the level of rates the opposite holds.
  This pass did not read any quotes, so it cannot say why. Explanations we have **not** tested include:
  1. Feedback on strong essays may put recommended phrasing in quotation marks more often. Short "quotes"
     of a phrase the essay only partly contains would count as changed. The 1b reading found such stock
     phrases.
  2. Feedback on weak essays may mark its corrections with rewrite cues more often, which takes them out of
     the primary set.
  3. A short phrase may be matched against a near-miss passage in the essay that the feedback was not
     actually quoting.
- **Audit 1's reversed H2 is real but mostly formatting.** Weaker essays' quotes are character-exact more
  often even at fixed length. Most of the difference is how the model punctuates and marks up quotes from
  strong essays, not a difference in whether it keeps their words.
- For a quote checker (such as MV2's [quote-check](https://github.com/munimtechnologies/quote-check)), this
  suggests sorting flagged quotes by length and showing the short ones first. It also suggests treating a
  4-6-word quote that matches only part of an essay passage as "possible suggested phrasing", not a
  misquote.

## Deviations from the plan

None in data, method, tests or verdict rules. All five predictions were stated as "difference above zero",
and all five came out with the whole 95% CI below zero.

## Limits

- The predictions were informed by audit 1, 1b and two 30-quote readings, so this is not a blind test.
  The reversals show that those readings were a poor guide to the rates.
- Short quotes have the least context to match on. Some 4-6-word "changed" quotes may be phrases the
  feedback suggested rather than quoted, or may have been matched to the wrong passage. This pass cannot
  tell these apart from real misquotes. A reading of a sample, done by a human, would be needed.
- Length and band are not independent of the essay's topic or the feedback prompt. Band is the dataset's
  label, not a new rating.
- 1b's classes inherit 1b's limits: elision is read generously, bold is taken as a marked correction, and
  change counts are read against audit 1's closest passage.
- This covers one model (GLM-4.7), one exam genre and one dataset.

## Reproduce

```bash
sh setup-2.sh          # fetches the pinned checker and explain.py and hash-checks them with audit.py
python -m unittest -v
python length.py --data glm47_final.jsonl --out length.json --workers 3
```

Apache-2.0 (code), CC BY 4.0 (text). MV2, Munim, Inc., mv2@munimtech.com.
