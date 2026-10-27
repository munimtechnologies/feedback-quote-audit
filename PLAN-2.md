# Plan 2: do longer quotes change the student's words more, and do weaker essays get more changed quotes?

feedback-quote-audit, audit 2. By MV2 of Munim, Inc. Made with AI agents working in his name.
Written 2026-10-27, after the results of audit 1 and follow-up 1b and before this pass ran. The sealed
run's setup refuses to start until this file is public in the repository. Apache-2.0 (code), CC BY 4.0 (text).

## Why

Follow-up 1b ([RESULTS-1b.md](RESULTS-1b.md)) found that, once Markdown formatting and "..." are allowed
for, 95.7% of GLM-4.7's quotes keep the student's words. 4.3% change them, and 2.8% change them without
marking it. Two questions stay open:

- **Length.** Are the changes concentrated in long quotes? The review samples suggested that some long
  "quotes" are really whole sentences rewritten into a better version. If so, a teacher checking quotes
  should look hardest at long ones.
- **Band.** Audit 1's H2 came out reversed: essays at band 5.5 or below had a *higher* exact rate than
  essays at 7.0 or above. 1b showed that the exact rate mostly measures formatting. Measured with 1b's
  classes, and with quote length held fixed, do weaker essays (which have more errors to fix silently) get
  *more* changed quotes?

## What was already seen before this plan

Everything in RESULTS.md, results.json, RESULTS-1b.md and explain.json, including:

- Audit 1's exact rate for 4-25-word quotes only (35.6%) against 37.7% for all lengths, which implies that
  quotes over 25 words are more often exact.
- The distribution of words changed per changed-words quote: 1 word 1,326; 2 words 1,311; 3 words 267;
  4 or more 1,014.
- The raw band difference in exact rate: +11.0 points (low minus high).
- Two 30-quote review samples. In the 1b sample, the whole-sentence rewrites were among the longest quotes.

No rate of word changes by quote length, and no band breakdown of 1b's classes, has been computed or seen.

## Data and code

The same pinned file as audits 1 and 1b (SHA-256 `3b5eea94...69494`), the same checker (feedback-commons
v0.8.0), audit 1's `audit.py` (commit `0d1c75a`) and 1b's `explain.py` (commit `d298ed9`). Both are
imported, not copied. Only the feedback field (`evaluation`), primary set only (at least 4 words, no rewrite
cue, not a quote of the question), with 1b's classes. The pass must reproduce the earlier totals: 50,742
quotes, 19,148 exact, 2,193 word-changed, 1,434 unmarked word-changed, and 20,520 / 2,712 quotes in the
low / high band groups. If it does not, that is reported first.

## Method (fixed)

- Quote length = the checker's word count of the quote. Bins: 4-6, 7-10, 11-15, 16-25, 26+ words.
- Per bin: the exact rate, the formatting-only rate (matched at 1b's steps 1-5), the word-changed rate,
  the unmarked word-changed rate, and changed words per quoted word (the sum of audit 1's word-edit counts
  over word-changed quotes, divided by the words in all the bin's quotes).
- **Length tests** compare 26+-word quotes with 4-6-word quotes. The 95% CI of the difference comes from a
  percentile bootstrap over essays, paired (each resampled essay brings both its short and its long quotes).
- **Band tests** compare essays at band 5.5 or below with essays at 7.0 or above (audit 1's groups). Rates
  are length-standardised: each group's rate in three strata (4-10, 11-25, 26+ words) is weighted by the
  share of all primary-set quotes in that stratum. Weights are fixed from the full data. The 95% CI comes
  from a percentile bootstrap that resamples essays within each group independently. The raw, unstandardised
  difference is reported too.
- 10,000 resamples, seed `feedback-quote-audit-2-20261027`.

## Predictions (each is "difference above zero"; verdict on the 95% CI)

- **L1:** the word-changed rate is higher in 26+-word quotes than in 4-6-word quotes.
- **L2:** the unmarked word-changed rate is higher in 26+-word quotes than in 4-6-word quotes.
- **L3:** changed words per quoted word is higher in 26+-word quotes than in 4-6-word quotes. A longer quote
  has more words that could change, so L1 alone could hold even if every word had the same chance of
  changing. L3 asks whether each word is also more likely to change.
- **B1:** the length-standardised unmarked word-changed rate is higher at band 5.5 or below than at 7.0 or
  above.
- **B2:** the length-standardised word-changed rate is higher at band 5.5 or below than at 7.0 or above.

Verdicts: "held" if the CI lies above zero, "reversed" if it lies below, otherwise "no clear difference".
"Underpowered" if a length bin compared has fewer than 300 quotes, or a band group has fewer than 100
quotes in any stratum.

Also reported, with no prediction:

- **B3:** the length-standardised exact rate by band. Does audit 1's +11.0 survive holding length fixed?
- **B4:** the length-standardised formatting-only rate by band.
- The full per-bin table.

## Limits known in advance

- Length and band are not independent of the essay's content or the prompt.
- Band is the dataset's label, not a new rating.
- 1b's classes inherit its limits: elision read generously, bold taken as a marked correction, and change
  counts read against audit 1's closest passage.
- One model, one exam genre, one dataset.
- The predictions are informed by what is listed above. They are not blind to the dataset.

## Outputs

`length.json`: aggregate counts and rates only, with no essay or feedback text. No review sample is drawn
in this pass.
